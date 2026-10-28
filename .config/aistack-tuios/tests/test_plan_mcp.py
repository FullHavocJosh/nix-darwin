#!/usr/bin/env python3
"""Test the plan pane's own MCP config: tuios, Atlassian and GitHub, passed only to the plan pane."""

import importlib.util
import json
import os
import shlex
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        p = a.write_plan_mcp(os.path.join(tmp, "plan-mcp.json"))
        with open(p) as f:
            servers = json.load(f)["mcpServers"]
        check("plan MCP servers are tuios, atlassian, github", set(servers) == {"tuios", "atlassian", "github"},
              sorted(servers))
        check("github MCP is pinned", "@edjl/github-mcp@1.0.8" in servers.get("github", {}).get("args", []))

        run = types.SimpleNamespace(data={"panes": {}}, dir=tmp, state=tmp)
        cfg = {"claude_settings": os.path.join(tmp, "s"), "claude_mcp": "/builder-mcp"}
        body = a.claude_body(run, cfg, "plan", "sys", "hi", tmp, mcp=p)
        check("plan body uses the plan MCP", p in body)
        check("plan body keeps --strict-mcp-config", "--strict-mcp-config" in body)
        check("plan body skips the builder MCP", "/builder-mcp" not in body)
        body = a.claude_body(run, cfg, "plan", "sys", "hi", tmp)
        check("default body uses the builder MCP", "/builder-mcp" in body)

    with tempfile.TemporaryDirectory() as tmp:
        s = os.path.join(tmp, "settings.json")
        b = os.path.join(tmp, "backbone.json")
        with open(s, "w") as f:
            json.dump({"hooks": {"PreToolUse": [{"matcher": "x", "hooks": []}]}}, f)
        cfg = {"claude_settings": s, "claude_backbone": b}
        a.write_backbone_settings(cfg)
        with open(b) as f:
            pre = json.load(f)["hooks"]["PreToolUse"]
        guards = [e for e in pre if e.get("matcher") == "mcp__atlassian__.*|mcp__github__.*"]
        check("tuios hook kept", {"matcher": "x", "hooks": []} in pre)
        check("guard hook added", len(guards) == 1 and "plan_mcp_guard" in guards[0]["hooks"][0]["command"],
              json.dumps(pre))
        a.write_backbone_settings(cfg)
        with open(b) as f:
            data = json.load(f)
        pre = data["hooks"]["PreToolUse"]
        guards = [e for e in pre if e.get("matcher") == "mcp__atlassian__.*|mcp__github__.*"]
        check("guard hook not duplicated", len(guards) == 1, json.dumps(pre))
        deny = data.get("permissions", {}).get("deny", [])
        check("GitHub writes denied", all(t in deny for t in a.PLAN_MCP_WRITES), deny)
        cmd = guards[0]["hooks"][0]["command"] if guards else ""
        script = shlex.split(cmd)[-1] if cmd else ""
        check("guard script exists", os.path.isfile(script), script)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
