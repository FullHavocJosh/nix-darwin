#!/usr/bin/env python3
"""local-edit MCP server: one targeted file edit on the on-device coder model (Qwen3-Coder-30B-A3B), so Claude Code
can hand an edit to a free local model instead of writing every line itself. Registered from
.config/mcp/claude-desktop-mcp.json. Nothing leaves the machine: the model server listens on loopback only.

One tool:
  local_edit(instruction, file, start_line, end_line, test_cmd)   rewrites one region of one file, returns the diff

The model sees as little as possible: one file per call, and with start_line/end_line only that region plus a few
read-only lines around it (whole files only up to LOCAL_EDIT_WHOLE_LINES). Its reply replaces exactly those lines, so
nothing outside the region can change. If test_cmd fails, the model gets one fix attempt with the failure output.

The 30B model needs ~19 GB, too much to keep loaded next to the always-on 9B (gpa/gpc, pi, ainfo). So it is loaded on
demand: the first call starts llama-server on LOCAL_EDIT_PORT (~25 s to load), and the server is stopped once no edit
has run for LOCAL_EDIT_IDLE_S (120 s). A server another Claude session already started is reused, edits run one at a
time across sessions, and nobody stops the server while an edit holds the lock. Hosts below 32 GB do not download the
model; the tool then says it is unavailable. Stdlib only.
"""

import difflib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

HOME = os.path.expanduser("~")
MODEL_FILE = os.environ.get("LOCAL_EDIT_MODEL_FILE") or os.path.join(HOME, "models", "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf")
ALIAS = os.environ.get("LOCAL_EDIT_ALIAS", "qwen3-coder-30b")
PORT = int(os.environ.get("LOCAL_EDIT_PORT", "8082"))
CTX = int(os.environ.get("LOCAL_EDIT_CTX", "32768"))
IDLE_S = int(os.environ.get("LOCAL_EDIT_IDLE_S", "120"))
LOAD_TIMEOUT_S = int(os.environ.get("LOCAL_EDIT_LOAD_TIMEOUT_S", "240"))
EDIT_TIMEOUT_S = int(os.environ.get("LOCAL_EDIT_TIMEOUT_S", "900"))
TEST_TIMEOUT_S = int(os.environ.get("LOCAL_EDIT_TEST_TIMEOUT_S", "300"))
DIFF_MAX_LINES = int(os.environ.get("LOCAL_EDIT_DIFF_LINES", "150"))
LLAMA_SERVER = os.environ.get("LLAMA_SERVER_BIN") or shutil.which("llama-server") or "/run/current-system/sw/bin/llama-server"
WHOLE_MAX_LINES = int(os.environ.get("LOCAL_EDIT_WHOLE_LINES", "200"))  # larger files need a line range
RANGE_MAX_LINES = int(os.environ.get("LOCAL_EDIT_RANGE_LINES", "250"))
CONTEXT_LINES = int(os.environ.get("LOCAL_EDIT_CONTEXT_LINES", "5"))  # read-only lines shown around the region
MAX_OUT_TOKENS = int(os.environ.get("LOCAL_EDIT_MAX_TOKENS", "6144"))
STATE = os.path.join(os.environ.get("LOCAL_EDIT_STATE_DIR") or os.path.join(HOME, ".cache", "local-edit"))
LOCK = os.path.join(STATE, "edit.lock")  # held while an edit runs, by whichever session runs it
LAST = os.path.join(STATE, "last-used")  # mtime = last time any session used the model
PIDFILE = os.path.join(STATE, "server.pid")  # the running server, whichever session started it
BASE = f"http://127.0.0.1:{PORT}"
PROTOCOL = "2024-11-05"

INSTRUCTIONS = (
    "local_edit hands one file edit to the free on-device coder model: one file per call, ideally with start_line and "
    "end_line so the model sees only that region (plus a few read-only lines around it) and can change nothing else. "
    "Give an exact 'do exactly this' instruction ending with 'Change nothing else.', and a test_cmd when a check "
    "exists; then review the returned diff. For a change across several files, call it once per file. Use it instead "
    "of hand edits once a request touches 3+ files (a hook enforces this); make a single small or subtle edit "
    "yourself, and a pure pattern replacement as one sed or python command. It needs a gpr worktree, not a main "
    "checkout. If it is unavailable or fails, oczen_edit (OpenCode Zen Big Pickle) takes the same request."
)

_mutex = threading.Lock()


def touch_last():
    os.makedirs(STATE, exist_ok=True)
    with open(LAST, "a"):
        pass
    os.utime(LAST, None)


def serving():
    try:
        with urllib.request.urlopen(BASE + "/v1/models", timeout=2) as r:
            return f'"{ALIAS}"' in r.read().decode()
    except Exception:
        return False


def ensure_server():
    """Returns None when the model is ready, otherwise the reason it is not."""
    if serving():
        return None
    if not os.path.isfile(MODEL_FILE):
        return (f"the local coder model is not on this machine ({MODEL_FILE}); it is downloaded only on hosts with "
                "32 GB or more. Make the edit yourself.")
    if not os.path.exists(LLAMA_SERVER):
        return f"llama-server not found ({LLAMA_SERVER})"
    os.makedirs(STATE, exist_ok=True)
    log = open(os.path.join(STATE, "server.log"), "w")
    server = subprocess.Popen(
        [LLAMA_SERVER, "--model", MODEL_FILE, "--alias", ALIAS, "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", str(CTX), "--parallel", "1", "--jinja", "--n-gpu-layers", "99", "--flash-attn", "on",
         "--cache-type-k", "q8_0", "--cache-type-v", "q8_0"],
        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    with open(PIDFILE, "w") as fh:
        fh.write(str(server.pid))
    t0 = time.time()
    while time.time() - t0 < LOAD_TIMEOUT_S:
        if serving():
            return None
        if server.poll() is not None:
            return f"llama-server exited while loading the model; see {os.path.join(STATE, 'server.log')}"
        time.sleep(1)
    stop_server()
    return f"the model did not load within {LOAD_TIMEOUT_S} s"


def server_pid():
    """The pid in PIDFILE, only if that process is still our llama-server (a pid can be reused)."""
    try:
        pid = int(open(PIDFILE).read().strip())
        cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
    except (OSError, ValueError):
        return None
    return pid if ALIAS in cmd and f"--port {PORT}" in cmd else None


def stop_server():
    pid = server_pid()
    if pid:
        try:
            os.kill(pid, 15)
            for _ in range(30):
                time.sleep(0.5)
                try:
                    if os.waitpid(pid, os.WNOHANG)[0] == pid:
                        break  # our own child: reaped (a zombie still answers kill 0)
                except ChildProcessError:
                    pass  # started by another session: not ours to reap
                os.kill(pid, 0)
            else:
                os.kill(pid, 9)
        except OSError:
            pass  # gone
    try:
        os.remove(PIDFILE)
    except OSError:
        pass


def stop_if_unused(min_idle):
    """Stops the server when no session used it for min_idle seconds and no edit holds the lock."""
    with _mutex:
        if not server_pid():
            return
        try:
            idle = time.time() - os.path.getmtime(LAST)
        except OSError:
            idle = min_idle + 1
        if idle < min_idle:
            return
        os.makedirs(STATE, exist_ok=True)
        with open(LOCK, "a") as lf:
            try:
                fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)  # an edit is running in some session: keep it
            except OSError:
                return
            stop_server()
            fcntl.flock(lf, fcntl.LOCK_UN)


def idle_watch():
    while True:
        time.sleep(min(10, max(1, IDLE_S // 4)))
        stop_if_unused(IDLE_S)


def repo_root(path):
    r = subprocess.run(["git", "-C", os.path.dirname(path) or ".", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return os.path.realpath(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def main_checkout(root):
    """True when root is a repository's main checkout rather than a linked worktree. The context-guardian hook blocks
    Edit/Write there (work goes through gpr worktrees); it never sees this MCP tool, so the tool applies the rule."""
    def rp(arg):
        r = subprocess.run(["git", "-C", root, "rev-parse", "--path-format=absolute", arg], capture_output=True, text=True)
        return os.path.realpath(r.stdout.strip())
    return rp("--git-dir") == rp("--git-common-dir")


def resolve(f, base):
    return os.path.realpath(os.path.join(base, os.path.expanduser(f)))


def read(p):
    try:
        with open(p, errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def check_request(a, allow_main_env="LOCAL_EDIT_ALLOW_MAIN"):
    """One file and, optionally, a line range (1-based, inclusive). Returns (request, None) or (None, error result).
    Shared with oczen_mcp.py."""
    def fail(msg):
        return None, {"ok": False, "error": msg}
    instruction = str(a.get("instruction") or "").strip()
    f = str(a.get("file") or "").strip()
    if not instruction or not f:
        return fail("instruction and file are required (one file per call; call again for another file)")
    path = resolve(f, os.getcwd())
    probe = os.path.dirname(path)
    while probe and not os.path.isdir(probe):  # a new file in a new directory
        probe = os.path.dirname(probe)
    root = repo_root(os.path.join(probe, "x"))
    if not root or not path.startswith(root + os.sep):
        return fail(f"{path} is not inside a git repository")
    if main_checkout(root) and os.environ.get(allow_main_env) != "1":
        return fail(f"{root} is a main checkout: edits go in a gpr worktree (run gpr first, then pass the worktree's "
                    "file), the same rule the context-guardian hook applies to Edit and Write")
    rel = os.path.relpath(path, root)
    text = read(path)
    lines = text.splitlines(keepends=True) if text is not None else []
    s, e = a.get("start_line"), a.get("end_line")
    if s is None and e is None:
        if len(lines) > WHOLE_MAX_LINES:
            return fail(f"{rel} has {len(lines)} lines: give start_line and end_line for the part to change (at most "
                        f"{RANGE_MAX_LINES} lines), so the model sees only that")
        s, e = 1, len(lines)
    else:
        try:
            s, e = int(s if s is not None else e), int(e if e is not None else s)
        except (TypeError, ValueError):
            return fail("start_line and end_line must be line numbers")
        if text is None:
            return fail(f"{rel} does not exist; omit start_line/end_line to create it")
        if not 1 <= s <= e <= len(lines):
            return fail(f"lines {s}-{e} are outside {rel}, which has {len(lines)} lines")
        if e - s + 1 > RANGE_MAX_LINES:
            return fail(f"lines {s}-{e} are {e - s + 1} lines; split the edit into ranges of at most {RANGE_MAX_LINES}")
    return {"instruction": instruction, "path": path, "root": root, "rel": rel, "text": text, "lines": lines,
            "start": s, "end": e, "test_cmd": str(a.get("test_cmd") or "").strip()}, None


def run_test(req):
    cmd = req["test_cmd"]
    try:
        t = subprocess.run(cmd, shell=True, cwd=req["root"], capture_output=True, text=True, timeout=TEST_TIMEOUT_S)
        return {"cmd": cmd, "passed": t.returncode == 0, "tail": ((t.stdout or "") + (t.stderr or ""))[-1500:]}
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "passed": False, "tail": f"timed out after {TEST_TIMEOUT_S} s"}


def summarize(req, ok, secs, model, test=None, log=""):
    """The result both edit tools return: what changed (with counts), a capped diff, the test result, and the tail of
    the model's output when nothing changed or it failed."""
    old, new = req["text"], read(req["path"])
    d = list(difflib.unified_diff((old or "").splitlines(), (new or "").splitlines(), req["rel"], req["rel"],
                                  lineterm="", n=2))
    changed = []
    if old != new:
        changed.append({"file": req["rel"], "lines": f"{req['start']}-{req['end']}",
                        "added": sum(1 for x in d if x.startswith("+") and not x.startswith("+++")),
                        "removed": sum(1 for x in d if x.startswith("-") and not x.startswith("---")),
                        "created": old is None})
    out = {"ok": ok and bool(changed), "seconds": secs, "model": model, "changed": changed}
    out["diff"] = ("\n".join(d[:DIFF_MAX_LINES]) + f"\n[diff cut at {DIFF_MAX_LINES} lines; git diff for the rest]"
                   if len(d) > DIFF_MAX_LINES else "\n".join(d))
    if req["test_cmd"]:
        out["test"] = test or run_test(req)
        out["ok"] = out["ok"] and out["test"]["passed"]
    if not out["ok"] and log:
        out["log"] = "\n".join([x for x in log.splitlines() if x.strip()][-15:])
    if not changed:
        out["error"] = out.get("error") or "the model changed nothing; make the edit yourself"
    return out


SYSTEM = ("You rewrite one region of one file exactly as instructed. Reply with ONLY the new content of the region: "
          "no explanation, no markdown fences, no line numbers, no region tags. Keep the file's indentation and style. "
          "The lines outside the region are context only: never repeat them in your reply.")


def numbered(lines, first):
    return "".join(f"{first + i:>5}| {line}" if line.endswith("\n") else f"{first + i:>5}| {line}\n"
                   for i, line in enumerate(lines))


def build_prompt(req, region, failure=None):
    s, e, lines = req["start"], req["end"], req["lines"]
    before = lines[max(0, s - 1 - CONTEXT_LINES):s - 1]
    after = lines[e:e + CONTEXT_LINES]
    parts = [f"File: {req['rel']}", f"Instruction: {req['instruction']}", ""]
    if req["text"] is None:
        parts.append("The file does not exist yet: reply with its whole content.")
    if before:
        parts += ["Context before the region (read-only):", numbered(before, s - len(before)).rstrip("\n")]
    parts += [f'<region lines="{s}-{e}">', region.rstrip("\n"), "</region>"]
    if after:
        parts += ["Context after the region (read-only):", numbered(after, e + 1).rstrip("\n")]
    if failure:
        parts += ["", "Your previous version of the region (shown above) failed this check:",
                  f"$ {failure['cmd']}", failure["tail"], "Fix the region so the check passes."]
    parts += ["", f"Reply with the new content for lines {s}-{e} only."]
    return "\n".join(parts)


def complete(prompt, region):
    """One chat completion on the local model. Returns (text, error)."""
    max_tokens = min(MAX_OUT_TOKENS, max(512, int(len(region) / 3 * 1.6) + 512))
    est = (len(SYSTEM) + len(prompt)) / 3 + max_tokens  # ~3 characters per token for code
    if est > CTX * 0.9:
        return None, f"the request is too large for the model's {CTX}-token context; give a smaller line range"
    body = {"model": ALIAS, "temperature": 0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=EDIT_TIMEOUT_S) as r:
            choice = json.load(r)["choices"][0]
    except Exception as exc:
        return None, f"the local model call failed: {type(exc).__name__}: {exc}"
    if choice.get("finish_reason") == "length":
        return None, "the model hit its output limit; give a smaller line range"
    return choice["message"].get("content") or "", None


def clean(reply, region):
    """The model's reply as region text: fences and stray region tags removed, the region's final newline kept."""
    lines = reply.strip("\n").split("\n")
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    lines = [x for x in lines if not x.strip().startswith(("<region", "</region"))]
    text = "\n".join(lines)
    if text and (region.endswith("\n") or not region):
        text += "\n"
    return text


def splice(req, new_region):
    lines = req["lines"]
    out = "".join(lines[:req["start"] - 1]) + new_region + "".join(lines[req["end"]:])
    os.makedirs(os.path.dirname(req["path"]), exist_ok=True)
    with open(req["path"], "w") as fh:
        fh.write(out)


def local_edit(a):
    req, err = check_request(a)
    if err:
        return err
    region = "".join(req["lines"][req["start"] - 1:req["end"]])
    os.makedirs(STATE, exist_ok=True)
    with open(LOCK, "a") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)  # one edit at a time, across sessions
        try:
            with _mutex:
                why = ensure_server()
            if why:
                return {"ok": False, "error": why}
            touch_last()
            t0 = time.time()
            reply, why = complete(build_prompt(req, region), region)
            if why:
                return {"ok": False, "error": why, "seconds": round(time.time() - t0)}
            new_region = clean(reply, region)
            splice(req, new_region)
            test = run_test(req) if req["test_cmd"] else None
            if test and not test["passed"]:  # one fix attempt, with the failure output
                reply, why = complete(build_prompt(req, new_region, failure=test), new_region)
                if not why:
                    splice(req, clean(reply, new_region))
                    test = run_test(req)
            secs = round(time.time() - t0)
            touch_last()
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
    return summarize(req, True, secs, ALIAS, test=test, log=reply)


TOOLS = {
    "local_edit": (
        local_edit,
        (
            "Edit one file with the free on-device coder model instead of your own Edit/Write: an exact instruction "
            "and, ideally, start_line/end_line so it sees and changes only that region. One file per call; returns "
            "the diff and the test result."
        ),
        {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "Exactly what to change in the region: names, signatures, edge cases. End with 'Change nothing else.'"},
                "file": {"type": "string", "description": "The one file to edit or create (relative to the working directory, or absolute), in a gpr worktree."},
                "start_line": {"type": "integer", "description": "First line of the region to rewrite (1-based). Omit both for a small whole file or a new file."},
                "end_line": {"type": "integer", "description": "Last line of the region to rewrite (inclusive)."},
                "test_cmd": {"type": "string", "description": "Optional shell command that exits 0 when the edit is right; a failure gets one fix attempt."},
            },
            "required": ["instruction", "file"],
        },
    ),
}


def handle(req):
    m = req.get("method")
    if m == "initialize":
        return {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                "serverInfo": {"name": "local-edit", "version": "0.1.0"}, "instructions": INSTRUCTIONS}
    if m == "ping":
        return {}
    if m == "tools/list":
        # anthropic/alwaysLoad: Claude Code loads the tool upfront instead of behind ToolSearch (one turn fewer)
        return {"tools": [{"name": n, "description": d, "inputSchema": s, "_meta": {"anthropic/alwaysLoad": True}}
                          for n, (_, d, s) in TOOLS.items()]}
    if m == "tools/call":
        p = req.get("params", {})
        tool = TOOLS.get(p.get("name"))
        if not tool:
            return {"content": [{"type": "text", "text": f"unknown tool {p.get('name')}"}], "isError": True}
        out = tool[0](p.get("arguments") or {})
        return {"content": [{"type": "text", "text": json.dumps(out, indent=1)}], "isError": not out.get("ok")}
    return None


def main():
    threading.Thread(target=idle_watch, daemon=True).start()
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except ValueError:
                continue
            if "id" not in req:
                continue
            try:
                res = handle(req)
                msg = ({"jsonrpc": "2.0", "id": req["id"], "result": res} if res is not None else
                       {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "method not found"}})
            except Exception as e:
                msg = {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(msg) + "\n")
            sys.stdout.flush()
    finally:
        # The session ended: do not leave a 19 GB model behind. Another session that needs it loads it again; one
        # whose edit is running keeps it, and its own idle watch stops it afterwards.
        stop_if_unused(0)


def watch_until_stopped():
    """`--stop-when-idle`: started detached by coder_pi.py (aidev's 30B builder), which has no MCP session to run
    idle_watch. Stops the server after IDLE_S without use, then exits; one watcher at a time."""
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, "watcher.lock"), "a") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return  # another watcher is on it
        while server_pid():
            time.sleep(min(10, max(1, IDLE_S // 4)))
            stop_if_unused(IDLE_S)


if __name__ == "__main__":
    if sys.argv[1:] == ["--stop-when-idle"]:
        watch_until_stopped()
    else:
        main()
