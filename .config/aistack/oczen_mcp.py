#!/usr/bin/env python3
"""bigpickle MCP server: file edits by OpenCode Zen's free Big Pickle model (`opencode run --auto`), for Claude Code.
Registered from .config/mcp/claude-desktop-mcp.json; not on the work laptop (no Zen key there, and the server is
excluded for that host) and not given to OpenCode itself.

One tool:
  bigpickle_edit(instruction, files, test_cmd, read_only_files)   same request and result as local_edit

local_edit (on-device, nothing leaves the machine) stays the first choice. bigpickle_edit is for when local_edit is
unavailable (the 30B is not on this host) or failed, or the change needs more than the local model managed. Big
Pickle runs in the cloud on OpenCode Zen, is faster and was more exact in testing (a 10-line edit in 83 s, spec-exact),
and OpenCode auto-formats every file it edits, so an unformatted file can show format-only hunks. It uses the same
request checks and result format as local_edit (local_edit_mcp.py): git repository, linked gpr worktree only, named
files only. Stdlib only.
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
TIMEOUT_S = int(os.environ.get("BIGPICKLE_TIMEOUT_S", "900"))
PROTOCOL = "2024-11-05"

_spec = importlib.util.spec_from_file_location("local_edit_mcp", os.path.join(HERE, "local_edit_mcp.py"))
le = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(le)

INSTRUCTIONS = (
    "bigpickle_edit hands a multi-file edit to OpenCode Zen's free Big Pickle model (cloud). Prefer local_edit (on "
    "this machine); use bigpickle_edit when local_edit is unavailable or failed, or the change needs more than the "
    "local model managed. Same request as local_edit: exact instruction ending with 'Change nothing else.', every "
    "file it may change, a test_cmd; review the returned diff. It needs a gpr worktree, not a main checkout."
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


def bigpickle_edit(a):
    if not zen_key_present():
        return {"ok": False, "error": "no OpenCode Zen API key on this host; use local_edit or make the edit yourself"}
    req, err = le.check_request(a, allow_main_env="BIGPICKLE_ALLOW_MAIN")
    if err:
        return err
    root = req["root"]
    rel = [os.path.relpath(p, root) for p in req["paths"]]
    ro = [os.path.relpath(p, root) for p in req["readonly"]]
    prompt = (f"Edit only these files in this repository (create them if missing): {', '.join(rel)}.\n"
              + (f"You may read, but not change: {', '.join(ro)}.\n" if ro else "")
              + f"\n{req['instruction']}\n\n"
              + (f"When done, run `{req['test_cmd']}` and fix the files above until it passes.\n" if req["test_cmd"] else "")
              + "Do not change any other file, do not commit, and do not ask questions.")
    before = {p: le.read(p) for p in req["paths"]}
    # Keep OpenCode's herdr plugin away from the Claude pane this MCP server runs in.
    env = {k: v for k, v in os.environ.items() if not k.startswith("HERDR_")}
    t0 = time.time()
    try:
        p = subprocess.run([OPENCODE, "run", "--auto", "--model", MODEL, prompt], cwd=root, capture_output=True,
                           text=True, timeout=TIMEOUT_S, stdin=subprocess.DEVNULL, env=env)
        log, rc = (p.stdout or "") + (p.stderr or ""), p.returncode
    except subprocess.TimeoutExpired:
        log, rc = f"timed out after {TIMEOUT_S} s", 124
    except OSError as e:
        return {"ok": False, "error": f"cannot run opencode ({OPENCODE}): {e}"}
    out = le.summarize(req, before, rc, log, round(time.time() - t0), MODEL)
    if out["changed"]:
        out["note"] = "OpenCode auto-formats edited files; format-only hunks are expected in unformatted files"
    return out


TOOLS = {
    "bigpickle_edit": (
        bigpickle_edit,
        (
            "Make a multi-file edit with OpenCode Zen's free Big Pickle model (cloud) when local_edit is unavailable "
            "or failed: one precise instruction, the files, a test_cmd; returns changed files, the diff and the test "
            "result."
        ),
        {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "Exact change: what to do in which file, names, signatures, edge cases. End with 'Change nothing else.'"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "Every file it may change or create, inside one git repository (a gpr worktree)."},
                "test_cmd": {"type": "string", "description": "Optional shell command that exits 0 when the edit is right."},
                "read_only_files": {"type": "array", "items": {"type": "string"}, "description": "Optional files it may read but not change."},
            },
            "required": ["instruction", "files"],
        },
    ),
}


def handle(req):
    m = req.get("method")
    if m == "initialize":
        return {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                "serverInfo": {"name": "bigpickle", "version": "0.1.0"}, "instructions": INSTRUCTIONS}
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
        except Exception as e:
            msg = {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
