"""Tests for advisor_hook.py guard case-insensitivity and ~ expansion. Runs the hook as Claude Code does,
with JSON on stdin. Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_advisor_guard_case.py
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
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="advisor-"))
STATE = T + "/state"
AWS_CONFIG = T + "/aws-config"
open(AWS_CONFIG, "w").write(
    "[profile ops-ro]\nsso_role_name = OpsReadOnly\n[profile ops]\nsso_role_name = Admin\n"
)
HOME = os.path.expanduser("~")
UID = os.getuid()
ENV = {
    k: v
    for k, v in os.environ.items()
    if k not in ("CLAUDE_ADVISOR", "CLAUDE_CODE_SESSION_ID")
}
ENV.update(CLAUDE_ADVISOR_STATE=STATE, AWS_CONFIG_FILE=AWS_CONFIG)


def run(tool, tin, session="s1", env=None):
    ev = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tin,
        "session_id": session,
    }
    p = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(ev),
        capture_output=True,
        text=True,
        env={**ENV, **(env or {})},
    )
    out = p.stdout.strip()
    return json.loads(out)["hookSpecificOutput"] if out else None


def decision(tool, tin, **kw):
    d = run(tool, tin, **kw)
    return d["permissionDecision"] if d else None


print("guard case and ~ expansion")

# (a) Write to T/ai/guard/x, T/ai/GUARD/x, T/ai/Guard/advisor/x with AI_HOME=T/ai are all 'deny'
ai_home = T + "/ai"
check(
    "guard is refused in any letter case",
    all(
        decision("Write", {"file_path": p}, env={"AI_HOME": ai_home}) == "deny"
        for p in (
            ai_home + "/guard/x",
            ai_home + "/GUARD/x",
            ai_home + "/Guard/advisor/x",
        )
    ),
)

# (b) Write to T/ai/rfcs/x.md is allowed (None)
check(
    "rfcs under AI_HOME are allowed",
    decision("Write", {"file_path": ai_home + "/rfcs/x.md"}, env={"AI_HOME": ai_home})
    is None,
)

# (c) with env AI_HOME='~/aihome' and HOME set to a temp dir H, Write to H/aihome/rfcs/x.md is allowed and H/aihome/guard/x is denied
H = os.path.realpath(tempfile.mkdtemp(prefix="advisor-home-"))
aihome = "~/aihome"
# Need to set HOME env for the subprocess; the code uses os.path.expanduser("~") at import time but also respects HOME?
# Looking at line 35: HOME = os.path.expanduser("~"). In subprocess, we can control environment. But if HOME not in env passed,
# the module under test uses the original HOME from current process if we didn't override in ENV dict passed to subprocess?
# Wait - when we run subprocess, we create a new Python process. The module's line 35 reads from current process env?
# os.path.expanduser("~") uses $HOME if set, else falls back to getpwuid. So we need to pass HOME in env.
env_c = {"AI_HOME": aihome, "HOME": H}
check(
    "an AI_HOME starting with ~ is expanded",
    decision("Write", {"file_path": H + "/aihome/rfcs/x.md"}, env=env_c) is None
    and decision("Write", {"file_path": H + "/aihome/guard/x"}, env=env_c) == "deny",
)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
