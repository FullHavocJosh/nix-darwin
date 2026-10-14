"""Tests for rfc_check.py: the aidev RFC gate that fails a significant change with no approved or implemented RFC.

The script is run as a subprocess with --rfc-dir pointing at a temp dir and --changed holding the paths under test, so
nothing here depends on this repo's own git state.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_rfc_check.py
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "rfc_check.py")
T = os.path.realpath(tempfile.mkdtemp(prefix="rfc-check-"))
FAILS = []

RALPH = ".config/aistack/ralph_mcp.py"


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def run(changed, rfc_dir):
    """Run the script with the given changed paths and rfc dir; return (exit code, stdout+stderr)."""
    r = subprocess.run(
        [sys.executable, SCRIPT, "--rfc-dir", rfc_dir, "--changed", *changed],
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout + r.stderr


def newdir(name, rfcs=()):
    """A temp rfc dir holding the given (filename, file text) RFCs (and no others)."""
    d = os.path.join(T, name)
    os.makedirs(d)
    for fname, text in rfcs:
        open(os.path.join(d, fname), "w").write(text)
    return d


def rfc(status, touches=None):
    lines = ["---", "title: a change", f"status: {status}"]
    if touches is not None:
        lines.append("touches: " + ", ".join(touches))
    lines += ["---", "", "## 1. TL;DR", "", "Body.", ""]
    return "\n".join(lines)


print("rfc_check: no significant path")
code, out = run(["AIDEV.md"], newdir("empty"))
check(
    "a docs-only change exits 0", code == 0 and "rfc_check: ok" in out, f"{code} {out}"
)

print("rfc_check: a significant path with no covering RFC")
empty = newdir("empty2")
code, out = run([RALPH], empty)
check("an uncovered ralph_mcp.py exits 1", code == 1, f"{code} {out}")
check("the output names the path", f"RFC required: {RALPH}" in out, out)
check("the output points at the template", "rfc-template.md" in out, out)

for status in ("draft", "review"):
    d = newdir(f"{status}", [("0001-a.md", rfc(status, [RALPH]))])
    code, out = run([RALPH], d)
    check(
        f"an RFC with status {status} does not cover it (exit 1)",
        code == 1,
        f"{code} {out}",
    )

for status in ("approved", "implemented"):
    d = newdir(f"{status}", [("0001-a.md", rfc(status, [RALPH]))])
    code, out = run([RALPH], d)
    check(
        f"an RFC with status {status} touching it exits 0",
        code == 0 and "ok" in out,
        f"{code} {out}",
    )

other = newdir(
    "other", [("0001-a.md", rfc("approved", [".config/aistack/ralph_driver.py"]))]
)
code, out = run([RALPH], other)
check("an approved RFC touching a different file exits 1", code == 1, f"{code} {out}")
check("the uncovered path is still named", f"RFC required: {RALPH}" in out, out)

print("rfc_check: tests and docs are not significant")
code, out = run([".config/aistack/tests/x.py", "AIDEV.md"], newdir("empty3"))
check(
    "changes under tests/ and *.md docs exit 0",
    code == 0 and "ok" in out,
    f"{code} {out}",
)

print("rfc_check: malformed RFCs")
bogus = newdir("bogus", [("0001-a.md", rfc("bogus", [RALPH]))])
code, out = run([RALPH], bogus)
check("a bogus status exits 2", code == 2, f"{code} {out}")
check("it is reported as an invalid RFC", "invalid RFC: 0001-a.md" in out, out)

notouch = newdir("notouch", [("0001-a.md", rfc("approved"))])
code, out = run([RALPH], notouch)
check("an RFC without touches exits 2", code == 2, f"{code} {out}")
check("the reason is a missing touches", "touches" in out, out)

print("rfc_check: missing rfc dir, and README is not an RFC")
missing = os.path.join(T, "does-not-exist")
code, out = run(["AIDEV.md"], missing)
check(
    "a missing rfc dir behaves as empty (exit 0)",
    code == 0 and "ok" in out,
    f"{code} {out}",
)
readme = newdir("readme", [("README.md", "not an RFC, just prose\n")])
code, out = run([RALPH], readme)
check(
    "README.md is ignored, so the path is still uncovered", code == 1, f"{code} {out}"
)

print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
