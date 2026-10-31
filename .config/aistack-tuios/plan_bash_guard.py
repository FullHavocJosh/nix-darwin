#!/usr/bin/env python3
"""
Bash hook that denies grep, egrep, fgrep, and find commands in the plan pane.
Use rg for content search (rg -n PATTERN [path]) and fd or rg --files -g GLOB for files.
"""

import json
import re
import sys


def decide(ev):
    # Only process Bash tool events
    if ev.get('tool_name') != 'Bash':
        return (None, '')
    
    # Extract the command
    cmd = (ev.get('tool_input') or {}).get('command', '')
    
    # Check if command contains grep, egrep, fgrep, or find at the start of a command or pipeline segment
    if re.search(r'(^|[;&|(]\s*|&&\s*)(grep|egrep|fgrep|find)(\s|$)', cmd):
        return ('deny', 'aidev plan pane: use rg for content search (rg -n PATTERN [path]) and fd or rg --files -g GLOB for files; grep and find are blocked.')
    
    return (None, '')

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
                "permissionDecisionReason": reason
            }
        }))
        return 0
    
    except Exception:
        # Fail open - return silently on any error
        return 0

if __name__ == "__main__":
    sys.exit(main())