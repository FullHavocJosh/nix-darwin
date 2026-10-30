#!/usr/bin/env python3
"""Test the lean Claude panes: user-level settings dropped, ~/.ai plan notes allowed, WebSearch denied."""

import importlib.util
import json
import os
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
        run = types.SimpleNamespace(dir=tmp, state="/tmp/s", data={"panes": {}})
        cfg = {"claude_settings": "s", "claude_mcp": "m"}
        body = a.claude_body(run, cfg, "plan", "sys", "first", "/tmp")
        check("plan body drops the user settings", "--setting-sources project,local" in body, body)
        check("plan body keeps --strict-mcp-config", "--strict-mcp-config" in body, body)

        s = os.path.join(tmp, "s")
        with open(s, "w") as f:
            json.dump({}, f)
        cfg = {"claude_settings": s, "claude_backbone": os.path.join(tmp, "b")}
        a.write_backbone_settings(cfg)
        with open(cfg["claude_backbone"]) as f:
            perms = json.load(f)["permissions"]
        check("plan notes allowed", "Edit(~/.ai/**)" in perms["allow"], perms["allow"])
        check("plan note writes allowed", "Write(~/.ai/**)" in perms["allow"], perms["allow"])
        check("WebSearch denied", "WebSearch" in perms["deny"], perms["deny"])
        check("guard denied", "Edit(~/.ai/guard/**)" in perms["deny"], perms["deny"])
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
