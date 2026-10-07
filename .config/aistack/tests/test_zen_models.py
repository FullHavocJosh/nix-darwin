"""Tests for zen_models.py (tier 1 free-model choice). No network, no opencode.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_zen_models.py
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import zen_models as z

FAILS = []

def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond: FAILS.append(name)

def model(cost=0, tool=True, rel="2026-01-01", status=None):
    m = {"cost": {"input": cost, "output": cost}, "tool_call": tool, "release_date": rel}
    if status: m["status"] = status
    return m

POLICY = {"verified": "2026-10-06", "source": "https://opencode.ai/docs/zen/", "public_preferred": "big-pickle",
          "zero_retention": ["space-bunny-free", "longcat-2.5-preview-free"]}
def cat(**models): return {"opencode": {"models": models}}
ALL = {"big-pickle", "space-bunny-free", "longcat-2.5-preview-free", "other-free", "paid-one"}
BASE = cat(**{"big-pickle": model(), "space-bunny-free": model(), "longcat-2.5-preview-free": model(),
              "other-free": model(rel="2026-09-01"), "paid-one": model(cost=3)})

print("public repository")
r = z.choose(BASE, ALL, POLICY, private=False, source="cache", age_h=1)
check("Big Pickle when it is free and offered", r["model"] == "big-pickle" and not r["warnings"], r)
c = json.loads(json.dumps(BASE)); c["opencode"]["models"]["big-pickle"] = model(cost=1)
r = z.choose(c, ALL, POLICY, private=False)
check("a price on Big Pickle is reported loudly", r["warnings"] and "not a free Zen option anymore" in r["warnings"][0] and "no longer free" in r["warnings"][0], r["warnings"])
check("and a zero-retention free model replaces it", r["model"] == "space-bunny-free", r["model"])
r = z.choose(BASE, ALL - {"big-pickle"}, POLICY, private=False)
check("not offered to the account is reported", "not offered to this account" in r["warnings"][0], r["warnings"])
c = json.loads(json.dumps(BASE)); del c["opencode"]["models"]["big-pickle"]
r = z.choose(c, ALL, POLICY, private=False)
check("missing from the catalog means retired", "retired or renamed" in r["warnings"][0], r["warnings"])
c = json.loads(json.dumps(BASE)); del c["opencode"]["models"]["big-pickle"]; c["opencode"]["models"]["space-bunny-free"] = model(cost=2); c["opencode"]["models"]["longcat-2.5-preview-free"] = model(cost=2)
r = z.choose(c, ALL, POLICY, private=False)
check("without zero-retention models the newest other free model is used", r["model"] == "other-free", r["model"])
c = {"opencode": {"models": {"big-pickle": model(cost=1), "x": model(cost=1)}}}
r = z.choose(c, {"big-pickle", "x"}, POLICY, private=False)
check("no free model at all gives model None and a warning", r["model"] is None and r["warnings"], r)

print("private repository")
r = z.choose(BASE, ALL, POLICY, private=True)
check("first zero-retention free model, never Big Pickle", r["model"] == "space-bunny-free", r["model"])
c = json.loads(json.dumps(BASE)); c["opencode"]["models"]["space-bunny-free"] = model(cost=1)
r = z.choose(c, ALL, POLICY, private=True)
check("falls to the second zero-retention model and reports the first", r["model"] == "longcat-2.5-preview-free" and "space-bunny-free" in " ".join(r["warnings"]), r)
r = z.choose(BASE, {"big-pickle", "other-free"}, POLICY, private=True)
check("none available: no model (never a training model) and a warning", r["model"] is None and any("no free zero-retention" in w for w in r["warnings"]), r)

print("data quality warnings")
r = z.choose(BASE, None, POLICY, private=False)
check("unlistable account offers are flagged", any("unverified" in w for w in r["warnings"]), r["warnings"])
r = z.choose(BASE, ALL, POLICY, private=False, source="stale-cache", age_h=130)
check("a stale catalog is flagged with its age", any("130 h old" in w for w in r["warnings"]), r["warnings"])
r = z.choose(BASE, ALL, POLICY, private=False, today=time.mktime(time.strptime("2027-01-20", "%Y-%m-%d")))
check("an old policy file asks for a re-check against the docs", any("re-check" in w for w in r["warnings"]), r["warnings"])

print("command line")
d = tempfile.mkdtemp(); cf = os.path.join(d, "catalog.json"); pf = os.path.join(d, "policy.json")
json.dump(BASE, open(cf, "w")); json.dump(POLICY, open(pf, "w"))
def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = z.main(list(args))
    return rc, out.getvalue(), err.getvalue()
rc, out, _ = run("choose", "--catalog", cf, "--offered", ",".join(sorted(ALL)), "--policy", pf, "--private", "yes")
check("choose prints JSON with the model", rc == 0 and json.loads(out)["model"] == "space-bunny-free", out)
rc, out, _ = run("best", "--catalog", cf, "--offered", ",".join(sorted(ALL)), "--policy", pf)
check("best prints Big Pickle for other callers", rc == 0 and out.strip() == "big-pickle", out)
rc, out, err = run("best", "--catalog", cf, "--offered", "paid-one", "--policy", pf)
check("best exits 1 with the reason when nothing is free", rc == 1 and "not a free Zen option anymore" in err, err)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
