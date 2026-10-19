"""Tests for ai_home.py guards: rfcs/ may not resolve outside AI_HOME or into guard/ (RFC 0003).

AI_HOME points at a temp dir, so nothing here touches the real ~/.ai.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_ai_home_guard.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
T = os.path.realpath(tempfile.mkdtemp(prefix="ai-home-guard-"))
os.environ["AI_HOME"] = T
import ai_home

FAILS = []


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def link_rfcs(dest):
    rfcs = os.path.join(T, "rfcs")
    if os.path.islink(rfcs):
        os.unlink(rfcs)
    else:
        shutil.rmtree(rfcs, ignore_errors=True)
    os.symlink(dest, rfcs)


def raises(dest):
    link_rfcs(dest)
    try:
        ai_home.write_rfc("# Refused\n\nNo.")
        return False
    except PermissionError:
        return True


guard = os.path.join(T, "guard")
for variant in ("guard", "GUARD", "Guard"):
    os.makedirs(os.path.join(T, variant), exist_ok=True)
OUT = os.path.realpath(tempfile.mkdtemp(prefix="ai-home-outside-"))

p = ai_home.write_rfc("# Normal write\n\nYes.")
check(
    "a normal write_rfc returns a file under T/rfcs",
    p.startswith(os.path.join(T, "rfcs") + os.sep) and os.path.isfile(p),
    p,
)

check("rfcs symlinked into guard is refused", raises(guard))
check(
    "case variant",
    raises(os.path.join(T, "GUARD")) and raises(os.path.join(T, "Guard")),
)

link_rfcs(guard)
r = subprocess.run(
    [sys.executable, os.path.join(HERE, "..", "ai_home.py"), "--write-rfc", "-"],
    input="# From a script\n",
    capture_output=True,
    text=True,
    env={**os.environ, "AI_HOME": T},
)
check(
    "main() prints ai_home: <message> to stderr and returns 1",
    r.returncode == 1 and r.stderr.startswith("ai_home: "),
    f"rc={r.returncode} {r.stderr.strip()}",
)

check("rfcs symlinked outside AI_HOME is refused", raises(OUT))

emptied = all(
    not os.listdir(os.path.join(T, v)) for v in ("guard", "GUARD", "Guard")
) and not os.listdir(OUT)
check("a refused write creates no file", emptied)

saved_ai = os.environ.get("AI_HOME")
saved_home = os.environ.get("HOME")
H = os.path.realpath(tempfile.mkdtemp(prefix="ai-home-home-"))
os.environ["AI_HOME"] = "~/aih"
os.environ["HOME"] = H
tilde_ok = ai_home.home() == H + "/aih"
tilde_got = ai_home.home()
os.environ["AI_HOME"] = saved_ai
if saved_home is None:
    os.environ.pop("HOME", None)
else:
    os.environ["HOME"] = saved_home
check("home() expands a leading ~ in AI_HOME", tilde_ok, tilde_got)

print("\nFAILED: " + str(FAILS) if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
