#!/usr/bin/env python3
"""local-edit MCP server: file edits on the on-device coder model (Qwen3-Coder-30B-A3B through aider), so Claude Code
can hand a large, mechanical edit to a free local model instead of writing every line itself. Registered from
.config/mcp/claude-desktop-mcp.json. Nothing leaves the machine: the model server listens on loopback only.

One tool:
  local_edit(instruction, files, test_cmd, read_only_files)   edits the files, returns a compact result and the diff

The 30B model needs ~19 GB, too much to keep loaded next to the always-on 9B (gpa/gpc, pi, ainfo). So it is loaded on
demand: the first call starts llama-server on LOCAL_EDIT_PORT (~25 s to load), and the server is stopped once no edit
has run for LOCAL_EDIT_IDLE_S (120 s). A server another Claude session already started is reused, and nobody stops it
while an edit holds the lock. Hosts below 32 GB do not download the model; the tool then says it is unavailable.
Stdlib only.
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
AIDER = os.environ.get("AIDER_BIN") or shutil.which("aider") or "/opt/homebrew/bin/aider"
STATE = os.path.join(os.environ.get("LOCAL_EDIT_STATE_DIR") or os.path.join(HOME, ".cache", "local-edit"))
LOCK = os.path.join(STATE, "edit.lock")  # held while an edit runs, by whichever session runs it
LAST = os.path.join(STATE, "last-used")  # mtime = last time any session used the model
PIDFILE = os.path.join(STATE, "server.pid")  # the running server, whichever session started it
BASE = f"http://127.0.0.1:{PORT}"
PROTOCOL = "2024-11-05"

INSTRUCTIONS = (
    "Use local_edit instead of your own Edit/Write whenever a change touches 3+ files or needs 5+ edits and you can "
    "state it precisely: it runs on a free on-device model, so you write one instruction instead of every edit. "
    "Measured: 7 edits in 6 files took 3 turns and $0.09 through local_edit, 18 turns and $0.16 by hand. A purely "
    "pattern-based replacement is cheaper still as one sed or python command; if that is not possible or not "
    "allowed, use local_edit rather than editing by hand. Make single small or subtle edits "
    "yourself. Name every file it may change, end the instruction with 'Change nothing else.', pass test_cmd when a "
    "check exists, and review the returned diff. It needs a gpr worktree, not a main checkout. If it is "
    "unavailable or fails, bigpickle_edit (OpenCode Zen Big Pickle) takes the same request."
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


def resolve(files, base):
    out = []
    for f in files:
        p = os.path.realpath(os.path.join(base, os.path.expanduser(f)))
        out.append(p)
    return out


def read(p):
    try:
        with open(p, errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def check_request(a, allow_main_env="LOCAL_EDIT_ALLOW_MAIN"):
    """Validates an edit request. Returns (request, None) or (None, error result). Shared with bigpickle_mcp.py."""
    instruction = str(a.get("instruction") or "").strip()
    files = [str(x) for x in (a.get("files") or []) if str(x).strip()]
    if not instruction or not files:
        return None, {"ok": False, "error": "instruction and files are required"}
    base = os.getcwd()
    paths = resolve(files, base)
    readonly = resolve([str(x) for x in (a.get("read_only_files") or [])], base)
    root = repo_root(paths[0]) or (os.path.realpath(base) if repo_root(os.path.join(base, "x")) else None)
    if not root:
        return None, {"ok": False, "error": f"{paths[0]} is not inside a git repository"}
    outside = [p for p in paths + readonly if not (p == root or p.startswith(root + os.sep))]
    if outside:
        return None, {"ok": False, "error": f"files must be inside the repository {root}: {outside}"}
    if main_checkout(root) and os.environ.get(allow_main_env) != "1":
        return None, {"ok": False, "error": f"{root} is a main checkout: edits go in a gpr worktree (run gpr first, "
                      "then pass the worktree's files), the same rule the context-guardian hook applies to Edit and "
                      "Write"}
    req = {"instruction": instruction, "paths": paths, "readonly": readonly, "root": root,
           "test_cmd": str(a.get("test_cmd") or "").strip()}
    return req, None


def summarize(req, before, rc, log, secs, model, noise=()):
    """The result both edit tools return: changed files with counts, a capped diff, the test result, and the tail of
    the model's output when nothing changed or it failed."""
    root, test_cmd = req["root"], req["test_cmd"]
    changed, diff_lines = [], []
    for path in req["paths"]:
        old, new = before[path], read(path)
        if old == new:
            continue
        rel = os.path.relpath(path, root)
        d = list(difflib.unified_diff((old or "").splitlines(), (new or "").splitlines(), rel, rel, lineterm="", n=2))
        plus = sum(1 for x in d if x.startswith("+") and not x.startswith("+++"))
        minus = sum(1 for x in d if x.startswith("-") and not x.startswith("---"))
        changed.append({"file": rel, "added": plus, "removed": minus, "created": old is None})
        diff_lines += d
    out = {"ok": rc == 0 and bool(changed), "seconds": secs, "model": model, "changed": changed}
    if len(diff_lines) > DIFF_MAX_LINES:
        out["diff"] = "\n".join(diff_lines[:DIFF_MAX_LINES]) + f"\n[diff cut at {DIFF_MAX_LINES} lines; git diff for the rest]"
    else:
        out["diff"] = "\n".join(diff_lines)
    if test_cmd:
        try:
            t = subprocess.run(test_cmd, shell=True, cwd=root, capture_output=True, text=True, timeout=TEST_TIMEOUT_S)
            out["test"] = {"cmd": test_cmd, "passed": t.returncode == 0,
                           "tail": ((t.stdout or "") + (t.stderr or ""))[-1500:]}
        except subprocess.TimeoutExpired:
            out["test"] = {"cmd": test_cmd, "passed": False, "tail": f"timed out after {TEST_TIMEOUT_S} s"}
        out["ok"] = out["ok"] and out["test"]["passed"]
    if rc != 0 or not changed:
        out["log"] = "\n".join([x for x in log.splitlines() if x.strip() and not x.startswith(noise)][-15:])
        if not changed:
            out["error"] = "the model changed none of the files; make the edit yourself"
    return out


def local_edit(a):
    req, err = check_request(a)
    if err:
        return err
    root, paths = req["root"], req["paths"]
    os.makedirs(STATE, exist_ok=True)
    with open(LOCK, "a") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)  # one edit at a time, across sessions
        try:
            with _mutex:
                why = ensure_server()
            if why:
                return {"ok": False, "error": why}
            touch_last()
            before = {p: read(p) for p in paths}
            settings = os.path.join(STATE, "model-settings.yml")
            with open(settings, "w") as fh:
                fh.write(f"- name: openai/{ALIAS}\n  edit_format: diff\n  extra_params:\n    max_tokens: 4096\n"
                         "    temperature: 0\n")
            argv = [AIDER, "--model", f"openai/{ALIAS}", "--openai-api-base", BASE + "/v1", "--openai-api-key",
                    "sk-local", "--model-settings-file", settings, "--no-auto-commits", "--no-gitignore",
                    "--no-check-update", "--no-analytics", "--no-show-model-warnings", "--no-detect-urls",
                    "--yes-always", "--no-pretty", "--map-tokens", "0",
                    "--input-history-file", os.path.join(STATE, "input.history"),
                    "--chat-history-file", os.path.join(STATE, "chat.history.md")]
            for r in req["readonly"]:
                argv += ["--read", r]
            if req["test_cmd"]:
                argv += ["--test-cmd", req["test_cmd"], "--auto-test"]
            argv += ["--message", req["instruction"]] + paths
            t0 = time.time()
            try:
                p = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=EDIT_TIMEOUT_S,
                                   stdin=subprocess.DEVNULL, env={**os.environ, "BROWSER": "true"})
                log, rc = (p.stdout or "") + (p.stderr or ""), p.returncode
            except subprocess.TimeoutExpired:
                log, rc = f"timed out after {EDIT_TIMEOUT_S} s", 124
            secs = round(time.time() - t0)
            touch_last()
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
    out = summarize(req, before, rc, log, secs, ALIAS,
                    noise=("Tokens:", "Aider v", "Model:", "Git repo:", "Repo-map:", "Added ", "https://aider.chat"))
    if "has hit a token limit" in log:
        out["error"] = "the model hit its output limit; split the edit into smaller ones or make it yourself"
    return out


TOOLS = {
    "local_edit": (
        local_edit,
        (
            "Make a multi-file edit (3+ files or 5+ edits) with the free on-device coder model instead of your own "
            "Edit/Write: one precise instruction, the files, a test_cmd; returns changed files, the diff and the "
            "test result. Far fewer turns than editing by hand."
        ),
        {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "Exact change: what to do in which file, names, signatures, edge cases. End with 'Change nothing else.'"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "Every file it may change or create (paths relative to the working directory, or absolute), inside one git repository."},
                "test_cmd": {"type": "string", "description": "Optional shell command that exits 0 when the edit is right; failures are fed back to the model."},
                "read_only_files": {"type": "array", "items": {"type": "string"}, "description": "Optional files it may read for context but not change."},
            },
            "required": ["instruction", "files"],
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


if __name__ == "__main__":
    main()
