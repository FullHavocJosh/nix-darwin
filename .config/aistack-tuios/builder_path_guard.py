#!/usr/bin/env python3
"""
Bash hook that keeps the billed builder's rm, mv, cp, mkdir and touch inside its work dir.
Usage: builder_path_guard.py WORK_DIR (reads the PreToolUse event JSON on stdin).
"""

import json
import os
import re
import shlex
import sys

GUARDED = ("rm", "mv", "cp", "mkdir", "touch")


def check_segment(seg, wd):
    """A deny reason for one command segment, or None."""
    try:
        words = shlex.split(seg)
    except ValueError:
        if seg.strip().split(" ")[0] in GUARDED:
            return "builder: cannot parse this " + seg.strip().split(" ")[0] + " command; keep it simple."
        return None
    while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
        words.pop(0)
    if not words or words[0] not in GUARDED:
        return None
    verb = words[0]
    if "$" in seg or "`" in seg or "~" in seg:
        return f"builder: {verb} may not use $, backticks or ~; use a path inside {wd}."
    for arg in words[1:]:
        if arg.startswith("-"):
            if "/" in arg or "=" in arg:
                return f"builder: {verb} option with a path or value is not allowed ({arg}); pass paths as plain arguments."
            continue
        if ".." in arg.split("/"):
            return f"builder: {verb} may not use '..' in a path ({arg})."
        real = os.path.realpath(os.path.join(wd, arg))
        if real != wd and not real.startswith(wd + "/"):
            return f"builder: {verb} {arg} is outside the work dir {wd}."
        if verb == "rm" and real == wd:
            return f"builder: rm may not remove the work dir {wd}."
    return None


def decide(ev, wd):
    if ev.get("tool_name") != "Bash":
        return (None, "")
    cmd = (ev.get("tool_input") or {}).get("command", "")
    for seg in re.split(r"[;&|\n]+", cmd):
        reason = check_segment(seg, wd)
        if reason:
            return ("deny", reason)
    return (None, "")


def main():
    try:
        ev = json.load(sys.stdin)
        decision, reason = decide(ev, os.path.realpath(sys.argv[1]))
        if decision is None:
            return 0
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        }))
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
