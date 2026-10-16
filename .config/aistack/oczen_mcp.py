#!/usr/bin/env python3
"""oczen MCP server: one targeted file edit by OpenCode Zen's free Big Pickle model, for Claude Code. Registered from
.config/mcp/claude-desktop-mcp.json; not on the work laptop (no Zen key there, and the server is excluded for that
host) and not given to OpenCode itself.

One tool:
  oczen_edit(instruction, file, start_line, end_line, test_cmd)   same request and result as local_edit

local_edit (on-device, nothing leaves the machine) stays the first choice; oczen_edit is for when local_edit is
unavailable (the 30B is not on this host) or failed. It runs `opencode run --standalone --auto` (a private server, so
no shared background service with someone else's environment) with OpenCode's formatter turned off, and tells Big
Pickle to change only the given lines of the given file. Afterwards it checks that: a change outside the line range
puts the file back, and any other file it touched is restored or removed. It uses local_edit's request checks and
result format (local_edit_mcp.py): one file, a linked gpr worktree, optional line range. Stdlib only.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
HOME = os.path.expanduser("~")
MODEL = "opencode/big-pickle"
OPENCODE = os.environ.get("OPENCODE_BIN") or shutil.which("opencode") or "/opt/homebrew/bin/opencode"
TIMEOUT_S = int(os.environ.get("OCZEN_TIMEOUT_S", "900"))
PROTOCOL = "2024-11-05"

_spec = importlib.util.spec_from_file_location("local_edit_mcp", os.path.join(HERE, "local_edit_mcp.py"))
le = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(le)

INSTRUCTIONS = (
    "oczen_edit hands one file edit to OpenCode Zen's free Big Pickle model (cloud). Prefer local_edit (on this "
    "machine); use oczen_edit when local_edit is unavailable or failed. Same request as local_edit: one file per "
    "call, ideally start_line/end_line, an exact instruction ending with 'Change nothing else.', a test_cmd; changes "
    "outside the range are reverted. Review the returned diff. It needs a gpr worktree, not a main checkout."
)


def zen_key_present():
    """The same places _validate_opencode_zen (.zshrc_functions_ai) looks for an OpenCode Zen API key."""
    if os.environ.get("OPENCODE_ZEN_API_KEY"):
        return True
    for f in (".zshrc_envvars", ".zshrc_envvars_insecure", ".config/opencode/.env"):
        try:
            if "OPENCODE_ZEN_API_KEY" in open(os.path.join(HOME, f), errors="replace").read():
                return True
        except OSError:
            pass
    try:
        auth = json.load(open(os.path.join(HOME, ".local/share/opencode/auth.json")))
        return bool((auth.get("opencode") or {}).get("key"))
    except (OSError, ValueError):
        return False


def git_status(root):
    r = subprocess.run(["git", "-C", root, "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                       capture_output=True, text=True)
    out = {}
    for entry in r.stdout.split("\0"):
        if len(entry) > 3:
            out[entry[3:]] = entry[:2]
    return out


def undo_other_files(root, rel, before):
    """Restores tracked files and removes untracked ones that OpenCode changed besides the target file."""
    undone = []
    for path, code in git_status(root).items():
        if path == rel or before.get(path) == code:
            continue
        full = os.path.join(root, path)
        if code == "??":
            try:
                os.remove(full)
            except OSError:
                continue
        else:
            subprocess.run(["git", "-C", root, "checkout", "--", path], capture_output=True)
        undone.append(path)
    return undone


def outside_range(req):
    """True when the file now differs from its old content outside the requested line range."""
    old, new = req["lines"], (le.read(req["path"]) or "").splitlines(keepends=True)
    s, e = req["start"], req["end"]
    head, tail = old[:s - 1], old[e:]
    return new[:len(head)] != head or (tail and new[len(new) - len(tail):] != tail) or len(new) < len(head) + len(tail)


def oczen_edit(a):
    if not zen_key_present():
        return {"ok": False, "error": "no OpenCode Zen API key on this host; use local_edit or make the edit yourself"}
    req, err = le.check_request(a, allow_main_env="OCZEN_ALLOW_MAIN")
    if err:
        return err
    root, rel, s, e = req["root"], req["rel"], req["start"], req["end"]
    if req["text"] is None:
        scope = f"Create the file {rel}."
    elif (s, e) == (1, len(req["lines"])):
        scope = f"Edit only the file {rel}."
    else:
        region = "".join(req["lines"][s - 1:e])
        scope = (f"Edit only lines {s}-{e} of {rel}; every other line of the file must stay exactly as it is. "
                 f"Those lines are currently:\n{region}")
    prompt = (f"{scope}\n\n{req['instruction']}\n\n"
              + (f"When done, run `{req['test_cmd']}` and fix the region until it passes.\n" if req["test_cmd"] else "")
              + "Do not change any other file, do not commit, and do not ask questions.")
    status_before = git_status(root)
    # Keep OpenCode's herdr plugin away from the Claude pane this server runs in, and its formatter off: a reformat
    # of the whole file would break the line-range rule.
    env = {k: v for k, v in os.environ.items() if not k.startswith("HERDR_")}
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"formatter": False})
    t0 = time.time()
    try:
        # --agent build: the default agent is advisor (read-only); this is a builder run
        argv = [OPENCODE, "run", "--standalone", "--auto", "--agent", "build", "--model", MODEL, prompt]
        p = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=TIMEOUT_S,
                           stdin=subprocess.DEVNULL, env=env)
        log, rc = (p.stdout or "") + (p.stderr or ""), p.returncode
    except subprocess.TimeoutExpired:
        log, rc = f"timed out after {TIMEOUT_S} s", 124
    except OSError as exc:
        return {"ok": False, "error": f"cannot run opencode ({OPENCODE}): {exc}"}
    undone = undo_other_files(root, rel, status_before)
    reverted = req["text"] is not None and outside_range(req)
    if reverted:
        with open(req["path"], "w") as fh:
            fh.write(req["text"])
    out = le.summarize(req, rc == 0 and not reverted, round(time.time() - t0), MODEL, log=log)
    if undone:
        out["undone"] = undone
        out["note"] = "it also changed other files; those changes were undone"
    if reverted:
        out["ok"] = False
        out["error"] = f"it changed lines outside {s}-{e}; the file was put back. Give a wider range or edit it yourself"
    return out


TOOLS = {
    "oczen_edit": (
        oczen_edit,
        (
            "Edit one file with OpenCode Zen's free Big Pickle model (cloud) when local_edit is unavailable or failed: "
            "an exact instruction and, ideally, start_line/end_line; changes outside the range are reverted. Returns "
            "the diff and the test result."
        ),
        {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "Exactly what to change in the region. End with 'Change nothing else.'"},
                "file": {"type": "string", "description": "The one file to edit or create, in a gpr worktree."},
                "start_line": {"type": "integer", "description": "First line of the region (1-based). Omit both for a small whole file or a new file."},
                "end_line": {"type": "integer", "description": "Last line of the region (inclusive)."},
                "test_cmd": {"type": "string", "description": "Optional shell command that exits 0 when the edit is right."},
            },
            "required": ["instruction", "file"],
        },
    ),
}


def handle(req):
    m = req.get("method")
    if m == "initialize":
        return {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                "serverInfo": {"name": "oczen", "version": "0.2.0"}, "instructions": INSTRUCTIONS}
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
        except Exception as exc:
            msg = {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32603, "message": str(exc)}}
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
