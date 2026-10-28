#!/usr/bin/env python3
"""
Read-only guard hook for the plan pane's Atlassian and GitHub tools.
This hook ensures that only read-only tools from Atlassian and GitHub MCPs
are allowed in the plan pane, while all write operations are denied.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
GUARD = os.environ.get("AIDEV_TUIOS_GUARD") or os.path.join(os.path.dirname(HERE), "ainfo", "ainfo_guard.py")
GUARDED = ("mcp__atlassian__", "mcp__github__")

def load_guard():
    spec = importlib.util.spec_from_file_location("ainfo_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def decide(ev):
    tool = ev.get("tool_name", "")
    
    # If tool doesn't have a guarded prefix, allow it
    if not any(tool.startswith(prefix) for prefix in GUARDED):
        return (None, "")
    
    # Load the guard module and check the decision
    why = load_guard().mcp_decision(tool, ev.get("tool_input") or {})
    if why is None:
        return ("allow", "")
    
    return ("deny", f"aidev plan pane: {tool} is read-only here ({why}). Do not retry or work around it; tell the user the exact call and let them decide.")

def main():
    try:
        ev = json.load(sys.stdin)
        decision, reason = decide(ev)
        
        # If no decision was made (None), return silently
        if decision is None:
            return 0
        
        # Otherwise print the decision
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason or "aidev plan pane: read-only"
            }
        }))
        return 0
    
    except Exception as e:
        # Fail closed - deny on any error
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"plan_mcp_guard error ({e})"
            }
        }))
        return 0

if __name__ == "__main__":
    sys.exit(main())