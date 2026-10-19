"""Tests for advisor_hook.py: AI_HOME/guard is refused in any letter case, and a leading ~ in AI_HOME is expanded.
Runs the hook as Claude Code does, with JSON on stdin.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_advisor_guard_case.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(os.path.dirname(HERE), "advisor_hook.py")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="advisor-"))
ENV = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_ADVISOR", "CLAUDE_CODE_SESSION_ID")}
ENV.update(CLAUDE_ADVISOR_STATE=T + "/state")


def decision(tool, tin, env):
    ev = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tin, "session_id": "s1"}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(ev), capture_output=True, text=True, env={**ENV, **env})
    out = p.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


print("guard case and ~ expansion")
AI = {"AI_HOME": T + "/ai"}
check("guard is refused in any letter case", all(
    decision("Write", {"file_path": T + p}, AI) == "deny" for p in ("/ai/guard/x", "/ai/GUARD/x", "/ai/Guard/advisor/x")))
check("rfcs under AI_HOME are allowed", decision("Write", {"file_path": T + "/ai/rfcs/x.md"}, AI) is None)

# os.path.expanduser reads $HOME, so the hook's ~ resolves to H
H = os.path.realpath(tempfile.mkdtemp(prefix="advisor-home-"))
TILDE = {"AI_HOME": "~/aihome", "HOME": H}
check("an AI_HOME starting with ~ is expanded",
      decision("Write", {"file_path": H + "/aihome/rfcs/x.md"}, TILDE) is None
      and decision("Write", {"file_path": H + "/aihome/guard/x"}, TILDE) == "deny")

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
