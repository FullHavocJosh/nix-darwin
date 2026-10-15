"""Tests for `aidev --handoff DIR` (ralph_mcp.py --handoff): a plan written in an interactive Claude Code session runs
without pi and without a billed planning call. Uses the fake ralph-tui and fake gpr; no AI, no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_handoff.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def project():
    p = os.path.realpath(tempfile.mkdtemp(prefix="handoff-proj-"))
    os.system(f"cd {p} && git init -q && git -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m init")
    st = os.path.realpath(tempfile.mkdtemp(prefix="handoff-state-"))
    return p, st


def plan_dir(prd, verify):
    d = os.path.realpath(tempfile.mkdtemp(prefix="handoff-plan-"))
    json.dump(prd, open(d + "/prd.json", "w"))
    json.dump(verify, open(d + "/verify.json", "w"))
    return d


def handoff(p, st, d):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AISTACK_", "RALPH_"))}
    env.update(RALPH_MCP_ROOTS=p, AISTACK_STATE_DIR=st, AISTACK_WORKTREE_MODE="create",
               AISTACK_WORKTREE_CMD=os.path.join(HERE, "fake-gpr.sh"), RALPH_TUI_BIN=os.path.join(HERE, "fake-ralph.py"),
               AISTACK_WORKER_AGENT="worker", AISTACK_FALLBACK_AGENT="fallback", AISTACK_REVIEW_AGENT="reviewer",
               AISTACK_DRIVER=os.path.join(ROOT, "ralph_driver.py"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "ralph_mcp.py"), "--handoff", p, d],
                       capture_output=True, text=True, env=env, timeout=120)
    try:
        return r.returncode, json.loads(r.stdout)
    except ValueError:
        return r.returncode, {"raw": r.stdout + r.stderr}


def wait_done(st, rid, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = json.load(open(f"{st}/runs/{rid}/state.json"))
        if s.get("state") in ("done", "failed", "lost"):
            return s
        time.sleep(0.5)
    return s


PRD = {"name": "add-flag", "title": "Add a flag", "description": "d", "userStories": [
    {"id": "T1", "title": "t1", "description": "create done_T1.txt", "acceptanceCriteria": ["done_T1.txt exists"],
     "priority": 1}]}
VERIFY = {"T1": "test -f done_T1.txt"}

print("a valid plan starts a run in a new worktree")
p, st = project()
rc, out = handoff(p, st, plan_dir(PRD, VERIFY))
check("exit 0 and started", rc == 0 and out.get("started"), out)
check("worktree created through gpr", out.get("worktree_created") and "/.worktrees/aistack-add-flag-" in out.get("work_dir", ""), out)
check("events path is reported", out.get("events", "").endswith(f"runs/{out.get('run_id')}/events.jsonl"), out)
rev = json.load(open(st + "/plan-review.json")) if os.path.exists(st + "/plan-review.json") else None
check("the plan is recorded as written by the Claude Code session (review gate passed, then consumed)",
      rev is None and json.load(open(st + "/plan/prd.json"))["userStories"][0]["passes"] in (False, True), rev)
check("verify strings become lists", json.load(open(st + "/plan/verify.json"))["T1"] == ["test -f done_T1.txt"])
check("PLAN.txt says no billed planning call", "no billed planning call" in open(st + "/plan/PLAN.txt").read())
if out.get("started"):
    s = wait_done(st, out["run_id"])
    check("the run finishes and the task is verified", s.get("state") == "done", s)

print("refusals")
p, st = project()
bad = json.loads(json.dumps(PRD)); bad["userStories"][0].pop("acceptanceCriteria")
rc, out = handoff(p, st, plan_dir(bad, VERIFY))
check("an invalid plan is refused with the problems", rc == 1 and not out.get("started") and any("acceptanceCriteria" in x for x in out.get("problems", [])), out)
check("and nothing is written to the plan dir", not os.path.exists(st + "/plan/prd.json"))
rc, out = handoff(p, st, plan_dir(PRD, {"T1": "test -f a | grep b"}))
check("a verify command with shell syntax is refused", rc == 1 and any("no shell syntax" in x for x in out.get("problems", [])), out)
os.makedirs(f"{st}/runs/20990101-000000")
json.dump({"state": "running", "pid": os.getpid()}, open(f"{st}/runs/20990101-000000/state.json", "w"))
rc, out = handoff(p, st, plan_dir(PRD, VERIFY))
check("an active run is not disturbed", rc == 1 and "still active" in out.get("problem", "") and not os.path.exists(st + "/plan/prd.json"), out)
rc, out = handoff(p, st, "/nonexistent-dir")
check("a missing plan dir is refused", rc == 1 and not out.get("started"), out)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
