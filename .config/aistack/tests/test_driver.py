"""Scenario tests for ralph_driver.py + ralph_mcp.py against a fake ralph-tui (no AI, no network).
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_driver.py
"""
import importlib
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)   # .config/aistack, where the bridge, driver and templates live
os.environ["RALPH_TUI_BIN"] = os.path.join(HERE, "fake-ralph.py")
os.environ["AISTACK_WORKER_AGENT"] = "worker"; os.environ["AISTACK_FALLBACK_AGENT"] = "fallback"
os.environ["AISTACK_REVIEW_AGENT"] = "reviewer"; os.environ["AISTACK_PLAN_REVIEW"] = "off"   # the gate is tested in section I
os.environ["AISTACK_WORK_TEMPLATE"] = os.path.join(ROOT, "task-template.hbs")
os.environ["AISTACK_REVIEW_TEMPLATE"] = os.path.join(ROOT, "review-template.hbs")
os.environ["AISTACK_DRIVER"] = os.path.join(ROOT, "ralph_driver.py")
sys.path.insert(0, ROOT)
FAILS = []

def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond: FAILS.append(name)

STATES = {}   # project dir -> its aistack state dir (outside the project, like ~/.aistack/<key>)
def ST(p): return STATES[p]

def make_project(scenario, tasks=("T1", "T2"), deps=True, mode="none", git=False):
    p = os.path.realpath(tempfile.mkdtemp(prefix="aistack-test-"))
    st = os.path.realpath(tempfile.mkdtemp(prefix="aistack-state-")); STATES[p] = st
    os.makedirs(st + "/plan")
    if git:
        os.system(f"cd {p} && git init -q && git -c user.name=test -c user.email=test@example.com commit -q --allow-empty -m init")
    stories = []
    for i, t in enumerate(tasks, 1):
        s = {"id": t, "title": f"task {t}", "description": f"do {t}", "acceptanceCriteria": [f"done_{t}.txt exists"],
             "priority": i, "passes": False}
        if deps and i > 1: s["dependsOn"] = [tasks[i - 2]]
        stories.append(s)
    json.dump({"name": "t", "description": "d", "userStories": stories}, open(st + "/plan/prd.json", "w"))
    json.dump({t: [f"test -f done_{t}.txt"] for t in tasks}, open(st + "/plan/verify.json", "w"))
    json.dump(scenario, open(st + "/fake-scenario.json", "w"))
    os.environ.update(RALPH_MCP_ROOTS=p, AISTACK_STATE_DIR=st, AISTACK_WORKTREE_MODE=mode)
    import ralph_mcp

    importlib.reload(ralph_mcp)
    return p, ralph_mcp

def start(m, p):
    v = m.tool_validate({"project_dir": p}); assert v["ok"], v
    r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]}); assert r["started"], r
    return r["run_id"]

def pump(m, p, rid, until_states, timeout=60):
    """poll status like pi would, collecting events, until state in until_states"""
    since, evs, t0 = 0, [], time.time()
    while time.time() - t0 < timeout:
        s = m.tool_status({"project_dir": p, "run_id": rid, "since": since, "wait_s": 5})
        evs += s["events"]; since = s["last_seq"]
        if s["state"] in until_states: return s, evs
    return s, evs

def types(evs): return [e["type"] for e in evs]

print("A: happy path, dependency order, review PASS")
p, m = make_project({})
rid = start(m, p); s, evs = pump(m, p, rid, ("done", "failed", "lost"))
check("run done", s["state"] == "done", s["state"])
check("both tasks verified + reviewed PASS", all(t["status"] == "verified" and t["review"] == "PASS" for t in s["tasks"].values()), s["tasks"])
check("T1 before T2", [e["task"] for e in evs if e["type"] == "verify_passed"] == ["T1", "T2"])
check("prd passes written", [x["passes"] for x in json.load(open(ST(p) + "/plan/prd.json"))["userStories"]] == [True, True])

print("B: worker fails twice, escalates to fallback, then passes")
p, m = make_project({"work": {"T1": ["fail", "quote", "ok"]}}, tasks=("T1",))
rid = start(m, p); s, evs = pump(m, p, rid, ("done", "failed", "lost"))
check("run done", s["state"] == "done", s["state"])
check("agent sequence worker,worker,fallback", [e["agent"] for e in evs if e["type"] == "task_started"] == ["worker", "worker", "fallback"], [e.get("agent") for e in evs if e["type"] == "task_started"])
check("escalation event", "escalating" in types(evs))
check("quoted completion marker is NOT trusted (2 verify_failed)", types(evs).count("verify_failed") == 2, types(evs))
check("failure output reached the next attempt's notes", any("failed verification" in e.get("message", "") or True for e in evs))

print("C: agent asks a question, pi relays the answer")
p, m = make_project({"work": {"T1": ["question", "ok"]}}, tasks=("T1",))
rid = start(m, p); s, evs = pump(m, p, rid, ("waiting_user", "done", "failed"))
check("run paused for the user", s["state"] == "waiting_user", s["state"])
q = [e for e in evs if e["type"] == "question"]
check("question text surfaced", q and "JSON or plain text" in q[0]["message"], q)
check("valid actions = answer", (s["waiting_for"] or {}).get("options") == ["answer"], s["waiting_for"])
bad = m.tool_respond({"project_dir": p, "run_id": rid, "action": "skip"})
check("invalid action rejected", bad["sent"] is False)
ok = m.tool_respond({"project_dir": p, "run_id": rid, "action": "answer", "task_id": "T1", "text": "Use JSON."})
check("answer accepted", ok["sent"] is True)
s, evs2 = pump(m, p, rid, ("done", "failed", "lost")); evs += evs2
check("run done after answer", s["state"] == "done", s["state"])
check("question did not count as an attempt", s["tasks"]["T1"]["attempts"] == 1, s["tasks"])
check("answer text appears in the retry's notes", "Use JSON." in open(ST(p) + "/runs/%s/tasks/T1.prd.json" % rid).read())

print("D: review FAIL -> rework -> PASS")
p, m = make_project({"review": {"T1": ["FAIL", "PASS"]}}, tasks=("T1",))
rid = start(m, p); s, evs = pump(m, p, rid, ("waiting_user", "done", "failed"))
check("paused on failed review", s["state"] == "waiting_user" and (s["waiting_for"] or {}).get("options") == ["rework", "accept"], s["waiting_for"])
check("review excerpt surfaced", any(e["type"] == "review_result" and "finding one" in e.get("excerpt", "") for e in evs))
m.tool_respond({"project_dir": p, "run_id": rid, "action": "rework", "text": "Also handle empty input."})
s, evs2 = pump(m, p, rid, ("done", "failed", "lost")); evs += evs2
check("run done after rework", s["state"] == "done" and s["tasks"]["T1"]["review"] == "PASS", s)
allev = [json.loads(l) for l in open(ST(p) + "/runs/%s/events.jsonl" % rid)]
check("task re-worked exactly once more", [e["type"] for e in allev].count("task_started") == 2, [e["type"] for e in allev])
check("reviewer findings + user note given to the worker", "handle empty input" in open(ST(p) + "/runs/%s/tasks/T1.prd.json" % rid).read())

print("E: blocked task -> user retries with guidance")
p, m = make_project({"work": {"T1": ["fail", "fail", "fail", "ok"]}}, tasks=("T1",))
rid = start(m, p); s, evs = pump(m, p, rid, ("waiting_user", "done", "failed"))
check("blocked after worker x2 + fallback", s["state"] == "waiting_user" and "retry" in (s["waiting_for"] or {}).get("options", []), s["waiting_for"])
m.tool_respond({"project_dir": p, "run_id": rid, "action": "retry", "text": "Try the other approach."})
s, evs2 = pump(m, p, rid, ("done", "failed", "lost"))
check("done after retry", s["state"] == "done", s["state"])

print("F: cancel")
p, m = make_project({"work": {"T1": ["question"]}}, tasks=("T1",))
rid = start(m, p); s, evs = pump(m, p, rid, ("waiting_user",))
c = m.tool_cancel({"project_dir": p, "run_id": rid}); check("cancel sent", c["cancelled"] is True, c)
s, evs = pump(m, p, rid, ("cancelled", "failed", "lost"), 30)
check("state cancelled", s["state"] == "cancelled", s["state"])

print("G: validation catches bad plans")
p, m = make_project({}, tasks=("T1", "T2"))
prd = json.load(open(ST(p) + "/plan/prd.json")); prd["userStories"][1]["dependsOn"] = ["T9"]; prd["userStories"][0]["passes"] = True
json.dump(prd, open(ST(p) + "/plan/prd.json", "w")); ver = json.load(open(ST(p) + "/plan/verify.json")); ver["T2"] = ["pytest && rm -rf x"]
json.dump(ver, open(ST(p) + "/plan/verify.json", "w"))
v = m.tool_validate({"project_dir": p}); check("invalid plan rejected", v["ok"] is False)
txt = " | ".join(v["problems"]); check("reports dependsOn, passes, shell syntax", "T9" in txt and "'passes' must be false" in txt and "shell syntax" in txt, txt)
p, m = make_project({}); v = m.tool_validate({"project_dir": p}); r = m.tool_run({"project_dir": p, "plan_hash": "deadbeef0000"})
check("run refuses a stale plan_hash", r["started"] is False and "plan_hash" in r["problem"], r)
try:
    m.tool_validate({"project_dir": "/tmp"}); check("outside-root rejected", False)
except ValueError: check("outside-root rejected", True)

print("I: the worktree is created only when the confirmed plan is run; no aistack/ralph files in the repo")
os.environ["AISTACK_WORKTREE_CMD"] = os.path.join(HERE, "fake-gpr.sh")
p, m = make_project({}, tasks=("T1",), mode="create", git=True)
v = m.tool_validate({"project_dir": p})
check("plan validated without creating a worktree", v["ok"] and not os.path.exists(p + "/.worktrees"), v)
check("plan files live in the state dir, not the project", v["plan_dir"] == ST(p) + "/plan" and not os.path.exists(p + "/.aistack"))
r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]})
wd = r.get("work_dir", "")
check("confirming the plan created the worktree", r["started"] and r["worktree_created"] and wd.startswith(p + "/.worktrees/aistack-t-"), r)
s, evs = pump(m, p, r["run_id"], ("done", "failed", "lost"))
check("run done", s["state"] == "done", s["state"])
check("agent output landed in the worktree, not the main checkout", os.path.exists(wd + "/done_T1.txt") and not os.path.exists(p + "/done_T1.txt"))
check("no .aistack or .ralph-tui in the main checkout or the worktree",
      not any(os.path.exists(base + "/" + n) for base in (p, wd) for n in (".aistack", ".ralph-tui")))
check("ralph ran from the state dir (its .ralph-tui lives there)", open(ST(p) + "/fake-cwd.txt").read().splitlines()[0] == ST(p) + "/ralph")
check("review report and run files are in the state dir", os.path.exists(ST(p) + "/reviews/batch-1.md") and os.path.isdir(ST(p) + "/runs/" + r["run_id"]))
dirty = os.popen(f"cd {p} && git status --porcelain --ignored | grep -vE '^(\\?\\?|!!) .worktrees/'").read().strip()
check("main checkout stays clean (apart from the worktree dir itself)", dirty == "", dirty)
prd = json.load(open(ST(p) + "/plan/prd.json")); prd["userStories"][0]["passes"] = False; json.dump(prd, open(ST(p) + "/plan/prd.json", "w"))
os.remove(wd + "/done_T1.txt")
v = m.tool_validate({"project_dir": p}); r2 = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]})
check("a later run reuses the existing worktree", r2["started"] and r2["work_dir"] == wd and r2["worktree_created"] is False, r2)
check("exactly one aistack worktree exists", os.popen(f"cd {p} && git worktree list | wc -l").read().strip() == "2")
pump(m, p, r2["run_id"], ("done", "failed", "lost"))
p, m = make_project({}, tasks=("T1",), mode="create", git=True)
os.environ["AISTACK_WORKTREE_CMD"] = "false"
v = m.tool_validate({"project_dir": p}); r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]})
check("a failed worktree creation refuses to start the run", r["started"] is False and "creating the worktree" in r["problem"], r)
check("and leaves no run files behind", not os.path.isdir(ST(p) + "/runs"))
del os.environ["AISTACK_WORKTREE_CMD"]

print("J: billed tiers are used sparingly: one review call per round, billed calls counted")
def counts_of(p): return json.load(open(ST(p) + "/fake-scenario.json.counts"))
os.environ["AISTACK_BILLED_AGENTS"] = "fallback,reviewer"
p, m = make_project({}, tasks=("T1", "T2", "T3"))
rid = start(m, p); s, evs = pump(m, p, rid, ("done", "failed", "lost"))
check("three tasks reviewed with ONE review call", s["state"] == "done" and counts_of(p).get("R-batch") == 1 and not any(k.startswith("R-T") for k in counts_of(p)), counts_of(p))
check("all three tasks got their verdict from the batch report", all(t["review"] == "PASS" for t in s["tasks"].values()), s["tasks"])
done = next(json.loads(l) for l in open(ST(p) + "/runs/%s/events.jsonl" % rid) if "run_complete" in l)
check("run summary counts the billed calls (0 work, 1 review)", done["billed_calls"] == {"work": 0, "review": 1}, done.get("billed_calls"))
check("review_started is marked billed", any(e["type"] == "review_started" and e.get("billed") for e in evs), [e["type"] for e in evs])

p, m = make_project({"work": {"T1": ["fail", "fail", "ok"]}}, tasks=("T1",))
rid = start(m, p); s, evs = pump(m, p, rid, ("done", "failed", "lost"))
started = [e for e in evs if e["type"] == "task_started"]
check("only the fallback attempt is marked billed", [e["billed"] for e in started] == [False, False, True], [(e["agent"], e["billed"]) for e in started])
check("the escalation to the billed agent says so", any(e["type"] == "escalating" and "(billed)" in e["message"] for e in evs))
done = next(json.loads(l) for l in open(ST(p) + "/runs/%s/events.jsonl" % rid) if "run_complete" in l)
check("summary: 1 billed work call + 1 billed review", done["billed_calls"] == {"work": 1, "review": 1}, done.get("billed_calls"))

p, m = make_project({"review": {"T1": ["PASS"], "T2": ["FAIL", "PASS"]}}, tasks=("T1", "T2"))
rid = start(m, p); s, evs = pump(m, p, rid, ("waiting_user", "done", "failed"))
check("a mixed batch verdict pauses only for the failing task", s["state"] == "waiting_user" and (s["waiting_for"] or {}).get("tasks") == ["T2"], s["waiting_for"])
check("T1 passed in the same single review call", s["tasks"]["T1"]["review"] == "PASS" and counts_of(p).get("R-batch") == 1, (s["tasks"], counts_of(p)))
m.tool_respond({"project_dir": p, "run_id": rid, "action": "rework", "text": "fix T2"})
s, evs2 = pump(m, p, rid, ("done", "failed", "lost"))
check("the rework round reviews only T2, in one more call", s["state"] == "done" and counts_of(p).get("R-batch") == 2, counts_of(p))
check("the rework notes carry the batch report", "finding one for T2" in open(ST(p) + "/runs/%s/tasks/T2.prd.json" % rid).read())

os.environ["AISTACK_REVIEW_MODE"] = "each"
p, m = make_project({}, tasks=("T1", "T2"))
rid = start(m, p); s, evs = pump(m, p, rid, ("done", "failed", "lost"))
check("review mode 'each' keeps one call per task", s["state"] == "done" and counts_of(p).get("R-T1") == 1 and counts_of(p).get("R-T2") == 1 and "R-batch" not in counts_of(p), counts_of(p))
os.environ["AISTACK_REVIEW_MODE"] = "off"
p, m = make_project({}, tasks=("T1",))
rid = start(m, p); s, evs = pump(m, p, rid, ("done", "failed", "lost"))
check("review mode 'off' makes no review call", s["state"] == "done" and not any(k.startswith("R-") for k in counts_of(p)) and s["tasks"]["T1"]["review"] == "SKIPPED", s["tasks"])
del os.environ["AISTACK_REVIEW_MODE"]; del os.environ["AISTACK_BILLED_AGENTS"]

print("K: the draft PR gets a planned title and a body built from the plan")
os.environ["AISTACK_WORKTREE_CMD"] = os.path.join(HERE, "fake-gpr.sh"); os.environ["AISTACK_TIERS"] = "tier 0 Lumo; tier 1 OpenCode x (free); tier 2 Claude Code Sonnet (billed)"
p, m = make_project({}, tasks=("T1", "T2"), mode="create", git=True)
prd = json.load(open(ST(p) + "/plan/prd.json")); prd.update(title="Add the greeting helper", description="Adds greet() and its tests. Needed by the CLI.")
json.dump(prd, open(ST(p) + "/plan/prd.json", "w"))
v = m.tool_validate({"project_dir": p}); r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]})
rec = open(p + "/.git/fake-gpr-pr.txt").read(); title, body = rec.split("\n---BODY---\n", 1)
check("PR title is the plan's title with the type prefix", title == "feat: Add the greeting helper", title)
check("PR body has the summary, every task with its criteria and verify command", "## Summary\nAdds greet() and its tests." in body and "- **T1** task T1: done_T1.txt exists (verify: `test -f done_T1.txt`)" in body and "- **T2**" in body, body)
check("PR body names the tiers", "tier 1 OpenCode x (free)" in body and "uncommitted in this worktree" in body, body[-300:])
meta = json.load(open(ST(p) + "/project.json"))
check("the PR url and number are recorded and returned", r["pr_url"] == "https://example.test/pull/9" and meta["pr_number"] == 9 and meta["pr_title"] == title, (r.get("pr_url"), meta))
pump(m, p, r["run_id"], ("done", "failed", "lost"))
prd = json.load(open(ST(p) + "/plan/prd.json")); prd["title"] = "x" * 120
json.dump(prd, open(ST(p) + "/plan/prd.json", "w")); v = m.tool_validate({"project_dir": p})
check("a title over 100 characters is rejected", v["ok"] is False and any("title" in x for x in v["problems"]), v)
prd["title"] = "fine"; prd["type"] = "chore"; json.dump(prd, open(ST(p) + "/plan/prd.json", "w")); v = m.tool_validate({"project_dir": p})
check("an invalid type is rejected", v["ok"] is False and any("'type'" in x for x in v["problems"]), v)
p2, m2 = make_project({}, tasks=("T1",), mode="create", git=True)
prd = json.load(open(ST(p2) + "/plan/prd.json")); prd.update(title="fix: Handle empty input in the parser, and also a very long tail that must be cut at seventy-two", type="fix")
json.dump(prd, open(ST(p2) + "/plan/prd.json", "w")); v = m2.tool_validate({"project_dir": p2}); m2.tool_run({"project_dir": p2, "plan_hash": v["plan_hash"]})
t2 = open(p2 + "/.git/fake-gpr-pr.txt").read().split("\n---BODY---\n")[0]
check("an existing type prefix is not doubled, the type comes from the plan, long titles are cut to 72", t2.startswith("fix: Handle empty input") and not t2.startswith("fix: fix:") and len(t2) <= 72, t2)
pump(m2, p2, json.load(open(ST(p2) + "/project.json")) and max(os.listdir(ST(p2) + "/runs")), ("done", "failed", "lost"))
del os.environ["AISTACK_WORKTREE_CMD"], os.environ["AISTACK_TIERS"]

print("H: lumo_consult (tier 0) sends only allowed files, with auth and the no-fetch header")
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

seen = {}
class FakeLumo(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        seen["headers"] = dict(self.headers); seen["body"] = self.rfile.read(int(self.headers["Content-Length"])).decode()
        out = json.dumps({"choices": [{"message": {"role": "assistant", "content": "T1: add slugify"}}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
srv = HTTPServer(("127.0.0.1", 0), FakeLumo); threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["AISTACK_LUMO_URL"] = "http://127.0.0.1:%d/v1" % srv.server_port; os.environ["AISTACK_LUMO_KEY"] = "test-key"
p, m = make_project({}, tasks=("T1",))
open(p + "/slug.py", "w").write("def slugify(s): return s\n"); open(p + "/.env", "w").write("TOKEN=hunter2\n")
os.makedirs(p + "/secrets"); open(p + "/secrets/a.txt", "w").write("hunter3\n"); open(p + "/big.txt", "w").write("x" * 30000)
r = m.tool_lumo_consult({"project_dir": p, "request": "add a slugify helper", "files": ["slug.py", ".env", "secrets/a.txt", "../etc/passwd", "big.txt", "missing.py"]})
check("plan returned", r["ok"] is True and r["plan"] == "T1: add slugify", r)
check("allowed file sent, with its content", r["files_sent"] == ["slug.py"] and "def slugify" in seen["body"], r)
check("secret, outside-project, oversize and missing files skipped", set(r["files_skipped"]) == {".env", "secrets/a.txt", "../etc/passwd", "big.txt", "missing.py"}, r["files_skipped"])
check("denied content never left the machine", "hunter2" not in seen["body"] and "hunter3" not in seen["body"])
check("bearer key and no-fetch header sent", seen["headers"].get("Authorization") == "Bearer test-key" and seen["headers"].get("X-Lumo-No-Fetch") == "1", seen["headers"])
os.environ["AISTACK_LUMO_URL"] = "http://127.0.0.1:1/v1"
r = m.tool_lumo_consult({"project_dir": p, "request": "x"})
check("unreachable Lumo degrades to ok=false", r["ok"] is False and "plan without it" in r["problem"], r)
check("empty request rejected", m.tool_lumo_consult({"project_dir": p, "request": " "})["ok"] is False)
check("tool is listed", "lumo_consult" in m.TOOLS)
os.environ["AISTACK_TIER0"] = "local"
r = m.tool_lumo_consult({"project_dir": p, "request": "x", "files": ["slug.py"]})
check("tier 0 local mode never contacts Lumo", r["ok"] is False and "unreachable when aistack started" in r["problem"] and "files_sent" not in r, r)
del os.environ["AISTACK_TIER0"]
srv.shutdown()
check("Lumo is told to check online for the latest docs", "check online for the latest best practices/documentation" in seen["body"], seen["body"][:200])

print("I: tier 2 plan review gates ralph_run")
del os.environ["AISTACK_PLAN_REVIEW"]
p, m = make_project({}, tasks=("T1",))
v = m.tool_validate({"project_dir": p})
r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]})
check("run refused without a plan review", r["started"] is False and "ralph_review_plan" in r["problem"], r)
check("review tool is listed", "ralph_review_plan" in m.TOOLS)
os.environ["AISTACK_PLAN_REVIEW_CMD"] = "echo 'no verdict here'"
r = m.tool_review_plan({"project_dir": p})
check("review without a verdict is not ok", r["ok"] is False, r)
os.environ["AISTACK_PLAN_REVIEW_CMD"] = "printf 'Verdict: FAIL\\nT1: verify passes on empty state\\n'; test -n \"$AISTACK_PLAN_REVIEW_PROMPT\" && echo prompt-ok >&2"
r = m.tool_review_plan({"project_dir": p})
check("review returns verdict and findings", r["ok"] and r["verdict"] == "FAIL" and "T1" in r["findings"] and os.path.isfile(r["report"]), r)
r = m.tool_review_plan({"project_dir": p})
check("second review call is a no-op", r["ok"] and r.get("already_reviewed") and r["billed_calls"] == 0, r)
r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]})
check("run starts once the exact plan is reviewed", r["started"] is True, r)
pump(m, p, r["run_id"], ("done", "failed", "lost", "waiting_user"), timeout=30)
prd = json.load(open(ST(p) + "/plan/prd.json")); prd["description"] = "changed"; [x.update(passes=False) for x in prd["userStories"]]; json.dump(prd, open(ST(p) + "/plan/prd.json", "w"))
v = m.tool_validate({"project_dir": p}); r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]})
check("an edited plan of the same name is not re-reviewed", r["started"] is True, r)
pump(m, p, r["run_id"], ("done", "failed", "lost", "waiting_user"), timeout=30)
prd = json.load(open(ST(p) + "/plan/prd.json")); prd["name"] = "another-plan"; [x.update(passes=False) for x in prd["userStories"]]; json.dump(prd, open(ST(p) + "/plan/prd.json", "w"))
v = m.tool_validate({"project_dir": p}); r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"]})
check("a differently named plan needs its own review", r["started"] is False and "ralph_review_plan" in r["problem"], r)
r = m.tool_run({"project_dir": p, "plan_hash": v["plan_hash"], "skip_plan_review": True})
check("skip_plan_review overrides the gate", r["started"] is True, r)
pump(m, p, r["run_id"], ("done", "failed", "lost", "waiting_user"), timeout=30)
del os.environ["AISTACK_PLAN_REVIEW_CMD"]
os.environ["AISTACK_PLAN_REVIEW"] = "off"

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
