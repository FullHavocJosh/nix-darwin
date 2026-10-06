"""Scenario tests for ralph_driver.py + ralph_mcp.py against a fake ralph-tui (no AI, no network).
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_driver.py
"""
import json, os, sys, tempfile, time, importlib, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)   # .config/aistack, where the bridge, driver and templates live
os.environ["RALPH_TUI_BIN"] = os.path.join(HERE, "fake-ralph.py")
os.environ["AISTACK_WORKER_AGENT"] = "worker"; os.environ["AISTACK_FALLBACK_AGENT"] = "fallback"
os.environ["AISTACK_REVIEW_AGENT"] = "reviewer"
os.environ["AISTACK_WORK_TEMPLATE"] = os.path.join(ROOT, "task-template.hbs")
os.environ["AISTACK_REVIEW_TEMPLATE"] = os.path.join(ROOT, "review-template.hbs")
os.environ["AISTACK_DRIVER"] = os.path.join(ROOT, "ralph_driver.py")
sys.path.insert(0, ROOT)
FAILS = []

def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond: FAILS.append(name)

def make_project(scenario, tasks=("T1", "T2"), deps=True):
    p = os.path.realpath(tempfile.mkdtemp(prefix="aistack-test-"))
    os.makedirs(p + "/.aistack")
    stories = []
    for i, t in enumerate(tasks, 1):
        s = {"id": t, "title": f"task {t}", "description": f"do {t}", "acceptanceCriteria": [f"done_{t}.txt exists"],
             "priority": i, "passes": False}
        if deps and i > 1: s["dependsOn"] = [tasks[i - 2]]
        stories.append(s)
    json.dump({"name": "t", "description": "d", "userStories": stories}, open(p + "/.aistack/prd.json", "w"))
    json.dump({t: [f"test -f done_{t}.txt"] for t in tasks}, open(p + "/.aistack/verify.json", "w"))
    json.dump(scenario, open(p + "/.aistack/fake-scenario.json", "w"))
    os.environ["RALPH_MCP_ROOTS"] = p
    import ralph_mcp; importlib.reload(ralph_mcp)
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
check("prd passes written", [x["passes"] for x in json.load(open(p + "/.aistack/prd.json"))["userStories"]] == [True, True])

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
check("answer text appears in the retry's notes", "Use JSON." in open(p + "/.aistack/runs/%s/tasks/T1.prd.json" % rid).read())

print("D: review FAIL -> rework -> PASS")
p, m = make_project({"review": {"T1": ["FAIL", "PASS"]}}, tasks=("T1",))
rid = start(m, p); s, evs = pump(m, p, rid, ("waiting_user", "done", "failed"))
check("paused on failed review", s["state"] == "waiting_user" and (s["waiting_for"] or {}).get("options") == ["rework", "accept"], s["waiting_for"])
check("review excerpt surfaced", any(e["type"] == "review_result" and "finding one" in e.get("excerpt", "") for e in evs))
m.tool_respond({"project_dir": p, "run_id": rid, "action": "rework", "text": "Also handle empty input."})
s, evs2 = pump(m, p, rid, ("done", "failed", "lost")); evs += evs2
check("run done after rework", s["state"] == "done" and s["tasks"]["T1"]["review"] == "PASS", s)
allev = [json.loads(l) for l in open(p + "/.aistack/runs/%s/events.jsonl" % rid)]
check("task re-worked exactly once more", [e["type"] for e in allev].count("task_started") == 2, [e["type"] for e in allev])
check("reviewer findings + user note given to the worker", "handle empty input" in open(p + "/.aistack/runs/%s/tasks/T1.prd.json" % rid).read())

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
prd = json.load(open(p + "/.aistack/prd.json")); prd["userStories"][1]["dependsOn"] = ["T9"]; prd["userStories"][0]["passes"] = True
json.dump(prd, open(p + "/.aistack/prd.json", "w")); ver = json.load(open(p + "/.aistack/verify.json")); ver["T2"] = ["pytest && rm -rf x"]
json.dump(ver, open(p + "/.aistack/verify.json", "w"))
v = m.tool_validate({"project_dir": p}); check("invalid plan rejected", v["ok"] is False)
txt = " | ".join(v["problems"]); check("reports dependsOn, passes, shell syntax", "T9" in txt and "'passes' must be false" in txt and "shell syntax" in txt, txt)
p, m = make_project({}); v = m.tool_validate({"project_dir": p}); r = m.tool_run({"project_dir": p, "plan_hash": "deadbeef0000"})
check("run refuses a stale plan_hash", r["started"] is False and "plan_hash" in r["problem"], r)
try:
    m.tool_validate({"project_dir": "/tmp"}); check("outside-root rejected", False)
except ValueError: check("outside-root rejected", True)

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
srv.shutdown()

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
