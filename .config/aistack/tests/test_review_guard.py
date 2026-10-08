"""Tests for gpa_review_guard.py: which AI review findings may block a commit. Uses a throwaway git repo; no model.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_review_guard.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "..", "gpa_review_guard.py")
FAILS = []

def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond: FAILS.append(name)

REPO = tempfile.mkdtemp(prefix="guard-")
def git(*a): return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=test@example.com", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()
def write(name, text): open(os.path.join(REPO, name), "w").write(text)
def run(cmd, obj):
    r = subprocess.run([sys.executable, GUARD, cmd], cwd=REPO, input=json.dumps(obj), capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr}
def finding(evidence, category="injection", severity="Critical", file="run.sh", issue="bad"):
    return {"file": file, "severity": severity, "category": category, "issue": issue, "recommendation": "fix", "evidence": evidence}

git("init", "-q"); git("checkout", "-q", "-b", "main")
write("run.sh", "#!/bin/sh\necho start\nold_line_that_was_here=1\n")
write("other.sh", "#!/bin/sh\n")
git("add", "-A"); git("commit", "-q", "-m", "init")
write("run.sh", "#!/bin/sh\necho start\nold_line_that_was_here=1\neval \"$USER_INPUT\"\nrm -rf \"$TARGET_DIR\"/*\n")
git("add", "-A")

print("round 1: evidence and category")
r = run("guard", {"issues": [
    finding('eval "$USER_INPUT"'),
    finding('+   eval   "$USER_INPUT"', issue="same line again, quoted with a plus and other spacing"),
    finding("curl http://macminim1.example/secret"),                  # invented: not in the diff
    finding("old_line_that_was_here=1"),                              # pre-existing, not an added line
    finding('rm -rf "$TARGET_DIR"/*', category="style"),              # real line, non-blocking category
    finding('rm -rf "$TARGET_DIR"/*', category="destructive-command", severity="Warning"),
    finding('eval "$USER_INPUT"', file="other.sh"),                   # right text, wrong file
    finding('eval "$USER_INPUT"', file="not-staged.sh"),
    {"file": "run.sh", "severity": "Critical", "category": "injection", "issue": "no evidence field", "recommendation": "x"},
    "not an object",
]})
check("guard runs", "error" not in r, str(r)[:300])
b, adv, dr = r.get("blocking", []), r.get("advisory", []), r.get("dropped", [])
check("the evidenced Critical injection finding blocks, once", len(b) == 1 and b[0]["evidence"] == 'eval "$USER_INPUT"', str(b)[:300])
check("it carries a fingerprint and code context", bool(b and b[0].get("fingerprint") and "eval" in b[0].get("context", "")))
why = " | ".join(d["why"] for d in dr)
check("invented, pre-existing and evidence-less findings are dropped", sum("not an added line" in d["why"] for d in dr) == 3, why)
check("an unchanged file and an unknown file are dropped", 2 == sum("not in the staged changes" in d["why"] for d in dr), why)
check("a non-object is dropped", any("not a finding object" in d["why"] for d in dr), why)
check("non-blocking category and Warning severity are advisory", len(adv) == 2 and all(a["why"] == "not a blocking category" for a in adv), str(adv)[:300])
fp = b[0]["fingerprint"] if b else ""
check("settle records the round", run("settle", {"blocking": b}).get("blocking") == 1)

print("round 2: nothing re-rolled, earlier finding carried")
r = run("guard", {"issues": [finding('rm -rf "$TARGET_DIR"/*', category="destructive-command")]})
b2 = r.get("blocking", [])
check("a new finding on a line that already passed is advisory", any("already passed" in a["why"] for a in r.get("advisory", [])), str(r)[:400])
check("the unresolved finding is carried even though the model did not repeat it", len(b2) == 1 and b2[0].get("carried") and b2[0]["fingerprint"] == fp, str(b2)[:300])
run("settle", {"blocking": b2})

print("round 3: fixed line, new line")
write("run.sh", "#!/bin/sh\necho start\nold_line_that_was_here=1\nrm -rf \"$TARGET_DIR\"/*\nsh -c \"$OTHER_INPUT\"\n")
git("add", "-A")
r = run("guard", {"issues": [finding('sh -c "$OTHER_INPUT"')]})
b3 = r.get("blocking", [])
check("the fixed finding is gone and the new line can block", len(b3) == 1 and b3[0]["evidence"] == 'sh -c "$OTHER_INPUT"' and not b3[0].get("carried"), str(b3)[:300])
fp3 = b3[0]["fingerprint"] if b3 else ""

print("waivers and confirmation")
r = run("guard", {"issues": [finding('sh -c "$OTHER_INPUT"')], "waive": [fp3]})
check("a waived finding does not block and is reported", not r.get("blocking") and [w["fingerprint"] for w in r.get("waived", [])] == [fp3], str(r)[:300])
run("settle", {"blocking": []})     # what gpa does when the confirmation pass rejects every candidate
check("a finding rejected by confirmation is not carried", not run("guard", {"issues": []}).get("blocking"))

print("state resets with HEAD")
git("commit", "-q", "-m", "next")
write("run.sh", "#!/bin/sh\necho start\nold_line_that_was_here=1\nrm -rf \"$TARGET_DIR\"/*\nsh -c \"$OTHER_INPUT\"\neval \"$USER_INPUT\"\n")
git("add", "-A")
r = run("guard", {"issues": [finding('eval "$USER_INPUT"')]})
check("after a commit the next change starts at round 1", r.get("round") == 1 and len(r.get("blocking", [])) == 1, str(r)[:300])

print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
