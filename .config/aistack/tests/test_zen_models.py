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
          "zero_retention": ["space-bunny-free", "longcat-2.5-preview-free"],
          "go_preferred": ["glm-5.3", "kimi-k2.7-code", "deepseek-v4-pro", "qwen3.8-max", "minimax-m3"],
          "go_zero_retention": []}
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

print("probing")
EXH = "Free usage exceeded, add credits  retrying in 10h 37m attempt 1"
st, det = z.classify("\x1b[31m" + EXH + "\x1b[0m", 1)
check("a Free usage exceeded line is exhausted with the retry time", st == "exhausted" and "10h 37m" in det, (st, det))
st, det = z.classify("Error: 429 Too Many Requests", 1)
check("a 429 line is exhausted", st == "exhausted", (st, det))
check("ok with code 0 is available", z.classify("ok\n", 0) == ("available", ""))
check("empty text with code 1 is unknown", z.classify("", 1) == ("unknown", "no output"))
st, det = z.classify("Free usage limit reached. Connect a provider...", 1)
check("Free usage limit reached is exhausted", st == "exhausted", (st, det))
def timeout_runner(cmd, **kw):
    raise z.subprocess.TimeoutExpired(cmd, 60, output=EXH.encode(), stderr=None)
rec = z.probe("big-pickle", runner=timeout_runner)
check("a timeout with exhausted partial output is exhausted", rec["state"] == "exhausted" and "10h 37m" in rec["detail"], rec)
seen = {}
def ok_runner(cmd, **kw):
    seen["cmd"] = cmd
    return z.subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")
rec = z.probe("big-pickle", runner=ok_runner)
check("an ok answer is available and the model is passed as opencode/<id>",
      rec["state"] == "available" and rec["model"] == "big-pickle" and "opencode/big-pickle" in seen["cmd"], (rec, seen))
seen = {}
def go_runner(cmd, **kw):
    seen["cmd"] = list(cmd)
    return z.subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")
rec = z.probe("opencode-go/glm-5.3", runner=go_runner)
check("probe builds --model opencode-go/glm-5.3 for that id",
      rec["state"] == "available" and "opencode-go/glm-5.3" in seen["cmd"], (rec, seen))
seen.clear()
rec = z.probe("big-pickle", runner=go_runner)
check("probe builds --model opencode/big-pickle for a bare id",
      rec["state"] == "available" and "opencode/big-pickle" in seen["cmd"], (rec, seen))

print("status")
sd = tempfile.mkdtemp(); z.STATUS_CACHE = os.path.join(sd, "sub", "status.json")
calls = []
def fake(states):
    def runner(cmd, **kw):
        mid = cmd[cmd.index("--model") + 1].split("/", 1)[1]
        calls.append(mid)
        if states.get(mid) == "exhausted":
            return z.subprocess.CompletedProcess(cmd, 1, stdout=EXH, stderr="")
        return z.subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")
    return runner
check("private candidates are the free zero-retention models in policy order",
      z.candidates(BASE, ALL, POLICY, True) == ["space-bunny-free", "longcat-2.5-preview-free"])
check("public candidates start with Big Pickle, then the newest free",
      z.candidates(BASE, ALL, POLICY, False, limit=3) == ["big-pickle", "other-free", "space-bunny-free"])
check("candidates puts opencode-go/ ids after the Zen ids for a public repo",
      z.candidates(BASE, ALL, POLICY, False, go_offered={"glm-5.3", "kimi-k2.7-code"}) == ["big-pickle", "other-free", "space-bunny-free", "longcat-2.5-preview-free", "opencode-go/glm-5.3", "opencode-go/kimi-k2.7-code"])
check("no Go ids for a private repo with an empty go_zero_retention",
      z.candidates(BASE, ALL, POLICY, True, go_offered={"glm-5.3"}) == ["space-bunny-free", "longcat-2.5-preview-free"])
check("skips a Go id missing from go_offered",
      z.candidates(BASE, ALL, POLICY, False, go_offered={"kimi-k2.7-code"}) == ["big-pickle", "other-free", "space-bunny-free", "longcat-2.5-preview-free", "opencode-go/kimi-k2.7-code"])
r = z.status(BASE, ALL, POLICY, False, do_probe=False, runner=fake({}))
check("do_probe False never calls the runner", not calls and all(m["state"] == "unprobed" for m in r["models"]) and r["best"] is None, (calls, r))
r = z.status(BASE, ALL, POLICY, False, do_probe=True, runner=fake({}))
check("probing stops after the first available", calls == ["big-pickle"] and r["best"] == "big-pickle"
      and [m["state"] for m in r["models"]][1:] == ["unprobed"] * 3, (calls, r))
n = len(calls)
r = z.status(BASE, ALL, POLICY, False, do_probe=True, runner=fake({}), now=time.time() + 5)
check("a fresh cache record is reused", len(calls) == n, calls)
calls.clear()
z.status(BASE, ALL, POLICY, False, do_probe=True, refresh=True, runner=fake({}))
check("refresh calls the runner again", calls == ["big-pickle"], calls)
calls.clear()
z.status(BASE, ALL, POLICY, False, do_probe=True, refresh=True, probe_all=True, limit=3, runner=fake({}))
check("probe_all probes every candidate", len(calls) == 3, calls)
os.remove(z.STATUS_CACHE); calls.clear()
r = z.status(BASE, ALL, POLICY, True, do_probe=True, runner=fake({"space-bunny-free": "exhausted", "longcat-2.5-preview-free": "exhausted"}))
check("all exhausted is reported", r["all_exhausted"] and r["best"] is None and len(calls) == 2, r)
os.remove(z.STATUS_CACHE)
SIX = [f"free-{i}" for i in range(6)]
C6 = cat(**{m: model() for m in SIX})
check("default candidate limit returns all six free models, limit=4 returns four",
      len(z.candidates(C6, set(SIX), POLICY, False)) == 6 and len(z.candidates(C6, set(SIX), POLICY, False, limit=4)) == 4)
calls.clear()
r = z.status(C6, set(SIX), POLICY, False, do_probe=True, runner=fake({m: "exhausted" for m in SIX}))
check("six exhausted candidates are all probed and all_exhausted is true", len(calls) == 6 and r["all_exhausted"], (calls, r))
os.remove(z.STATUS_CACHE)
def mixed(cmd, **kw):
    if "opencode/space-bunny-free" in cmd:
        return z.subprocess.CompletedProcess(cmd, 1, stdout="boom", stderr="")
    return z.subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")
r = z.status(BASE, ALL, POLICY, True, do_probe=True, runner=mixed)
check("best prefers available over unknown", r["best"] == "longcat-2.5-preview-free" and "space-bunny-free" in r["usable"], r)
os.remove(z.STATUS_CACHE)
rc, out, _ = run("status", "--catalog", cf, "--offered", ",".join(sorted(ALL)), "--policy", pf, "--private", "yes", "--json")
check("status without --probe exits 3 with unprobed models", rc == 3 and json.loads(out)["models"][0]["state"] == "unprobed", (rc, out))
rc, out, _ = run("status", "--catalog", cf, "--offered", "paid-one", "--policy", pf, "--private", "yes")
check("status exits 1 with no candidate", rc == 1 and "best: none" in out, (rc, out))

print("\nFAILED:%s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
