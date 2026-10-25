#!/usr/bin/env python3
"""MCP server (stdio, JSON-RPC 2.0) for aidev_test's research pane (pi on the local 9B).

Tools: repo_tree / repo_read / repo_grep (the real stack's budgeted research tools, imported from
~/.config/aistack/ralph_mcp.py unchanged), handoff (writes plan/brief.md for the plan pane), save_rfc.

The research pane has no tool that plans, runs or writes anywhere but the plan dir. The driver (aidev_test.py) sees
plan/brief.md appear and opens the plan pane on it; nothing here talks to tuios or another pane.

Safety: only inside RALPH_MCP_ROOTS; state under AIDEV_TEST_HOME (~/.ai/aidev_test), never ~/.ai/aidev.
"""

import importlib.util
import json
import os
import sys
import time

AI_HOME = os.path.expanduser(os.environ.get("AI_HOME") or "~/.ai")
AISTACK = os.path.expanduser(os.environ.get("AISTACK_DIR") or "~/.config/aistack")
os.environ["AISTACK_HOME"] = os.path.expanduser(os.environ.get("AIDEV_TEST_HOME") or os.path.join(AI_HOME, "aidev_test"))
os.environ.pop("AISTACK_STATE_DIR", None)

_spec = importlib.util.spec_from_file_location("ralph_mcp", os.path.join(AISTACK, "ralph_mcp.py"))
ralph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ralph)

PROTOCOL = "2024-11-05"
STR, INT = {"type": "string"}, {"type": "integer"}


def S(props, req):
    return {"type": "object", "properties": props, "required": req}


def renamed(fn):
    """A ralph_mcp research tool whose budget messages point at handoff instead of ralph_plan."""
    def call(a):
        out = fn(a)
        for k in ("problem", "note"):
            if isinstance(out.get(k), str):
                out[k] = out[k].replace("ralph_plan", "handoff")
        return out
    return call


def tool_handoff(a):
    """Write plan/brief.md: the request, the brief and the excerpts of the files that matter, with the real stack's
    file rules (deny list, line ranges, size caps)."""
    project = ralph.project_of(a)
    request = str(a.get("request") or "").strip()
    brief = str(a.get("brief") or "").strip()[:16000]
    if not request or not brief:
        return {"ok": False, "problem": "request and brief are both required"}
    files = [str(f) for f in (a.get("files") or [])][: ralph.LUMO_FILES_MAX]
    parts, skipped, total = [], [], 0
    for spec in files:
        _rel, text, why = ralph.plan_file(project, spec)
        if text is None:
            skipped.append(f"{spec}: {why}")
            continue
        text = text[: ralph.PLAN_FILE_ENTRY_MAX]
        if total + len(text) > ralph.PLAN_FILES_TOTAL_MAX:
            skipped.append(f"{spec}: over the {ralph.PLAN_FILES_TOTAL_MAX}-character total")
            continue
        total += len(text)
        parts.append(f"### {spec}\n\n```\n{text.rstrip()}\n```")
    pdir = ralph.plan_dir(project)
    os.makedirs(pdir, exist_ok=True)
    body = [f"# Research brief ({time.strftime('%Y-%m-%d %H:%M')})", "", "## Request", "", request, "",
            "## What the research found", "", brief, ""]
    if parts:
        body += ["## Files", ""] + parts + [""]
    if skipped:
        body += ["## Not included", ""] + [f"- {s}" for s in skipped] + [""]
    path = os.path.join(pdir, "brief.md")
    with open(path + ".tmp", "w") as fh:
        fh.write("\n".join(body))
    os.replace(path + ".tmp", path)
    ralph.RESEARCH_CALLS = 0
    return {"ok": True, "brief": path, "files_included": len(parts), "files_skipped": skipped,
            "next": "Tell the user that the plan pane (workspace 2) opens on this brief and that they talk to Claude "
                    "there. Then stop: you are done unless the user asks you something."}


TOOLS = {
    "repo_tree": (renamed(ralph.TOOLS["repo_tree"][0]), ralph.TOOLS["repo_tree"][1], ralph.TOOLS["repo_tree"][2]),
    "repo_read": (renamed(ralph.TOOLS["repo_read"][0]), ralph.TOOLS["repo_read"][1], ralph.TOOLS["repo_read"][2]),
    "repo_grep": (renamed(ralph.TOOLS["repo_grep"][0]), ralph.TOOLS["repo_grep"][1], ralph.TOOLS["repo_grep"][2]),
    "handoff": (
        tool_handoff,
        ("Hand the research to the plan pane, where Claude Code plans with the user. Call it once, when the research "
        "is done: request (the user's words plus their answers), brief (what you saw in the files: how the relevant "
        "code works, constraints, how it is tested; at most 16000 characters), files (at most 12 entries, "
        "'path:START-END' for the lines that matter, at most 200 lines each; a whole file only under 120 lines). "
        "Writes plan/brief.md; the driver then opens the plan pane on it."),
        S({"project_dir": STR, "request": STR, "brief": STR, "files": {"type": "array", "items": STR}},
          ["project_dir", "request", "brief"]),
    ),
    "save_rfc": ralph.TOOLS["ralph_save_rfc"],
}


def handle(req):
    m = req.get("method")
    if m == "initialize":
        return {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                "serverInfo": {"name": "aidev_test", "version": "0.1.0"}}
    if m == "ping":
        return {}
    if m == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": sch} for n, (_, d, sch) in TOOLS.items()]}
    if m == "tools/call":
        p = req.get("params", {})
        fn = TOOLS.get(p.get("name"))
        if not fn:
            return {"content": [{"type": "text", "text": f"unknown tool {p.get('name')}"}], "isError": True}
        try:
            return {"content": [{"type": "text", "text": json.dumps(fn[0](p.get("arguments") or {}), indent=1)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}
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
