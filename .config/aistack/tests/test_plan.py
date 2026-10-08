"""Tests for aidev's planning path: ralph_plan in ralph_mcp.py (Claude writes the plan) and the aidev dispatcher.
Claude is replaced by AISTACK_PLAN_CMD (a shell command that prints a canned reply); nothing here is billed.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_plan.py
"""
import http.server
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FAILS = []

def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond: FAILS.append(name)

T = os.path.realpath(tempfile.mkdtemp(prefix="plan-"))
PROJECT, STATE = T + "/proj", T + "/state"
os.makedirs(PROJECT + "/lib")
open(PROJECT + "/lib/small.py", "w").write("def small():\n    return 1\n")
open(PROJECT + "/lib/big.py", "w").write("".join(f"line{i} = {i}\n" for i in range(1, 4001)))   # > 24000 bytes
open(PROJECT + "/.env", "w").write("TOKEN=hunter2\n")
REPLY, COUNT, SEEN = T + "/reply.txt", T + "/count", T + "/prompt.txt"
os.environ.update(RALPH_MCP_ROOTS=PROJECT, AISTACK_STATE_DIR=STATE,
                  AISTACK_PLAN_CMD=f'echo x >> {COUNT}; printf "%s" "$AISTACK_PLAN_PROMPT" > {SEEN}; cat {REPLY}')
spec = importlib.util.spec_from_file_location("ralph_mcp", os.path.join(HERE, "..", "ralph_mcp.py"))
mcp = importlib.util.module_from_spec(spec); spec.loader.exec_module(mcp)

def calls(): return len(open(COUNT).read().split()) if os.path.exists(COUNT) else 0
def reply(obj): open(REPLY, "w").write(obj if isinstance(obj, str) else json.dumps(obj))
def plan(**kw): return mcp.tool_plan(dict({"project_dir": PROJECT, "request": "add a thing", "brief": "small() lives in lib/small.py"}, **kw))
def reset():
    for f in (STATE + "/plan-review.json", STATE + "/plan/prd.json", STATE + "/plan/verify.json"):
        if os.path.exists(f): os.remove(f)

GOOD = {"prd": {"name": "add-thing", "title": "Add a thing", "description": "Adds it.", "userStories": [
            {"id": "T1", "title": "Write it", "description": "Create lib/thing.py", "acceptanceCriteria": ["thing() returns 2"],
             "priority": 1, "passes": True, "dependsOn": []}]},
        "verify": {"T1": "python3 -m unittest tests.test_thing"}, "notes": ["assumed python3"]}

print("ralph_plan: a valid plan")
reply(GOOD)
r = plan(files=["lib/small.py", "lib/big.py:10-12", ".env", "../outside.py"], draft="T1: do it")
check("ok with a plan_hash", r.get("ok") is True and r.get("plan_hash"), str(r)[:300])
check("one billed call reported", r.get("billed_calls") == 1 and calls() == 1)
check("the plan text has the task and the note, and nothing is returned as data next to it",
      "T1  Write it" in r.get("present", "") and "assumed python3" in r.get("present", "") and "tasks" not in r and "notes" not in r, str(sorted(r))[:200])
check("the plan text is saved as PLAN.txt", open(STATE + "/plan/PLAN.txt").read().strip() == r.get("present", "").strip())
prd, verify = json.load(open(STATE + "/plan/prd.json")), json.load(open(STATE + "/plan/verify.json"))
check("passes is forced to false", prd["userStories"][0]["passes"] is False)
check("a single verify command becomes a list", verify["T1"] == ["python3 -m unittest tests.test_thing"])
check("the saved plan validates", mcp.tool_validate({"project_dir": PROJECT}).get("plan_hash") == r.get("plan_hash"))
check("ralph_run's review gate is satisfied", json.load(open(STATE + "/plan-review.json")).get("verdict") == "PLANNED")
pt0 = r.get("present", "")
check("skipped files are named in the plan text with the reason", all(x in pt0 for x in (".env (denied by policy)", "../outside.py (outside the project)")), pt0[-500:])
check("Claude is told to plan in one turn and how to ask for more", "Plan in ONE turn" in open(SEEN).read() and '"need"' in open(SEEN).read())
seen = open(SEEN).read()
check("prompt has request, brief and draft", all(x in seen for x in ("add a thing", "small() lives in lib/small.py", "T1: do it")))
check("prompt has the file and the numbered range", "def small():" in seen and "10: line10 = 10" in seen and "12: line12 = 12" in seen)
check("prompt has nothing outside the range or from .env", "line13 = 13" not in seen and "hunter2" not in seen)

print("ralph_plan: no second billed call")
r = plan()
check("already_planned without calling Claude", r.get("already_planned") is True and r.get("billed_calls") == 0 and calls() == 1, str(r)[:200])
check("it says what was planned", r.get("planned_request") == "add a thing")
r = plan(replan=True)
check("replan=true calls Claude again", r.get("ok") is True and calls() == 2)

print("ralph_plan: bad replies")
reset(); reply("Here is the plan:\n```json\n" + json.dumps(GOOD) + "\n```\nDone.")
check("a fenced reply with prose around it is parsed", plan().get("ok") is True)
reset(); bad = json.loads(json.dumps(GOOD)); bad["verify"]["T1"] = ["make test && echo ok"]; reply(bad)
r = plan()
check("an invalid plan is saved and its problems listed", r.get("ok") is False and any("no shell syntax" in p for p in r.get("problems", []))
      and os.path.exists(STATE + "/plan/prd.json"), str(r)[:300])
check("an invalid plan still carries the plan text with Claude's notes, and PLAN.txt exists", "assumed python3" in r.get("present", "")
      and "Lumo:" in r.get("present", "") and os.path.exists(STATE + "/plan/PLAN.txt"), r.get("present", "")[-300:])
check("an invalid plan still blocks a second billed call", plan().get("already_planned") is True)
r = mcp.tool_update_task({"project_dir": PROJECT, "task_id": "T1", "verify": ["python3 -m unittest tests.test_thing"]})
check("after the fix the plan text still has the notes and the Lumo line", r.get("ok") is True and "assumed python3" in r.get("present", "") and "Lumo:" in r.get("present", ""), r.get("present", "")[-300:])

print("verify commands: what needs a shell")
for cmd, bad in (('python3 -c "import sys; sys.exit(0 if 1 > 0 else 1)"', False), ("python3 -m unittest tests.test_thing", False),
                 ("grep -q 'a|b' file.txt", False), ("make test && echo ok", True), ("make test;echo ok", True), ("cat a | grep b", True),
                 ("echo hi > out.txt", True), ("echo $(date)", True), ("echo `date`", True), ('python3 -c "unbalanced', True)):
    check(("refused: " if bad else "accepted: ") + cmd, mcp.needs_shell(cmd) is bad)
reset(); n = calls(); reply("I could not do this.")
r = plan()
check("no JSON: ok false, raw output kept", r.get("ok") is False and os.path.exists(STATE + "/plan/claude-plan.raw.txt") and calls() == n + 1)
check("no JSON: no plan record is written", not os.path.exists(STATE + "/plan-review.json"))
check("empty request refused without a call", mcp.tool_plan({"project_dir": PROJECT, "request": " ", "brief": "x"}).get("ok") is False and calls() == n + 1)
reset(); reply(GOOD)
r = plan(brief="b" * 20000)
check("an oversized brief is cut and reported", "Cut to the size limit: brief." in r.get("present", "") and len(open(SEEN).read()) < 20000, r.get("present", "")[-300:])

print("ralph_plan: Lumo is consulted by the bridge, not by the chat agent")
asked = []
def fake_lumo(a):
    asked.append(a); return {"ok": True, "plan": "LUMO DRAFT: use kubeconform", "lumo": "http://127.0.0.1:8765/v1"}
real_lumo, mcp.tool_lumo_consult = mcp.tool_lumo_consult, fake_lumo
reset(); reply(GOOD); r = plan(files=["lib/big.py:10-12"])
check("without AISTACK_TIER0=lumo it is not asked", not asked and r.get("lumo") == "not available", str(r.get("lumo")))
os.environ["AISTACK_TIER0"] = "lumo"
reset(); r = plan(files=["lib/big.py:10-12"])
check("with a Lumo it is asked once, with the request, the brief and the files without ranges",
      len(asked) == 1 and "add a thing" in asked[0]["request"] and "small() lives" in asked[0]["request"] and asked[0]["files"] == ["lib/big.py"], str(asked)[:300])
pt = r.get("present", "")
check("the result carries the finished text for the user", all(x in pt for x in ("PLAN: Add a thing", "T1  Write it", "done when: thing() returns 2",
      "verify: python3 -m unittest tests.test_thing", "NOTES FROM CLAUDE:", "assumed python3", "Lumo: consulted", "say 'start'")), pt[:400])
check("its draft reaches Claude and the result says so", "LUMO DRAFT: use kubeconform" in open(SEEN).read() and r.get("lumo", "").startswith("consulted"), str(r.get("lumo")))
LONG = ("para one. " * 300 + "\n\n") * 18 + "WHOLE-MARKER"     # about 54,000 characters
second = []
def lumo_long(a, short="SHORT VERSION: " + "task with path lib/a.py. " * 40):
    if a.get("raw_prompt"):
        second.append(a["raw_prompt"]); return {"ok": True, "plan": short, "lumo": "x"}
    return {"ok": True, "plan": LONG, "lumo": "x"}
mcp.tool_lumo_consult = lumo_long
reset(); r = plan(); seen = open(SEEN).read()
check("a long draft goes back to Lumo once, in a fresh request that holds the whole draft", len(second) == 1 and "WHOLE-MARKER" in second[0]
      and "at most 1200 words" in second[0], str(len(second)))
check("Claude gets the short version, not the long one", "SHORT VERSION:" in seen and "WHOLE-MARKER" not in seen and len(seen) < 12000, str(len(seen)))
check("the plan text says the draft was shortened, with both sizes", "shortened by Lumo from" in r.get("present", ""), r.get("present", "")[-300:])
mcp.tool_lumo_consult = lambda a: {"ok": False, "problem": "timeout"} if a.get("raw_prompt") else {"ok": True, "plan": LONG, "lumo": "x"}
reset(); r = plan(); seen = open(SEEN).read()
check("when shortening fails the full draft (under 60000 characters) reaches Claude whole", mcp.PLAN_DRAFT_MAX == 60000 and "WHOLE-MARKER" in seen
      and "could not be shortened" in r.get("present", "") and "Cut to the size limit" not in r.get("present", ""), r.get("present", "")[-300:])
mcp.tool_lumo_consult = lambda a: {"ok": True, "plan": "short draft, one task", "lumo": "x"}
second.clear(); reset(); plan()
check("a short draft is not sent back", not second)
mcp.tool_lumo_consult = lambda a: {"ok": False} if a.get("raw_prompt") else {"ok": True, "plan": ("para one. " * 300 + "\n\n") * 24 + "TAIL-MARKER"}
reset(); r = plan(); seen = open(SEEN).read()
check("a longer draft is cut at a paragraph, marked, and reported", "[the draft was longer and is cut here]" in seen and "TAIL-MARKER" not in seen
      and "Cut to the size limit: draft." in r.get("present", ""), r.get("present", "")[-300:])
mcp.tool_lumo_consult = lambda a: {"ok": False, "problem": "connection refused"}
reset(); r = plan()
check("a Lumo failure does not stop the plan", r.get("ok") is True and r.get("lumo", "").startswith("failed"), str(r.get("lumo")))
mcp.tool_lumo_consult = real_lumo; os.environ.pop("AISTACK_TIER0")

print("ralph_update_task: the only way to change the plan")
reset(); reply(GOOD); h0 = plan().get("plan_hash")
def upd(**kw): return mcp.tool_update_task(dict({"project_dir": PROJECT}, **kw))
r = upd(task_id="T1", title="Write it well", verify=["python3 -m unittest tests.test_thing", "ruff check lib"])
prd, verify = json.load(open(STATE + "/plan/prd.json")), json.load(open(STATE + "/plan/verify.json"))
check("a field and the verify commands change, the rest stays", r.get("ok") is True and prd["userStories"][0]["title"] == "Write it well"
      and prd["userStories"][0]["description"] == "Create lib/thing.py" and len(verify["T1"]) == 2 and r.get("plan_hash") != h0, str(r)[:300])
r = upd(task_id="T2", title="Test it", description="Add tests/test_thing.py", acceptanceCriteria=["tests pass"], dependsOn=["T1"], verify=["python3 -m unittest"])
check("an unknown id adds a valid task after the others", r.get("ok") is True and [t["id"] for t in r.get("tasks", [])] == ["T1", "T2"]
      and json.load(open(STATE + "/plan/prd.json"))["userStories"][1]["priority"] == 2, str(r)[:300])
r = upd(task_id="T2", verify=["make test && echo ok"])
check("an invalid change is reported", r.get("ok") is False and any("no shell syntax" in p for p in r.get("problems", [])), str(r)[:200])
upd(task_id="T2", verify=["python3 -m unittest"])
r = upd(task_id="T1", remove=True)
prd = json.load(open(STATE + "/plan/prd.json"))
check("removing a task also removes its verify entry and references to it", r.get("ok") is True and [t["id"] for t in prd["userStories"]] == ["T2"]
      and prd["userStories"][0]["dependsOn"] == [] and "T1" not in json.load(open(STATE + "/plan/verify.json")), str(r)[:300])
check("nothing outside the plan dir was written", sorted(os.listdir(PROJECT)) == [".env", "lib"] and sorted(os.listdir(PROJECT + "/lib")) == ["big.py", "small.py"])
reset()
check("without a plan it refuses", upd(task_id="T1", title="x").get("ok") is False)

print("ralph_plan: long files must come as line ranges")
reset(); reply(GOOD); n = calls(); mcp._RANGES_ASKED.clear()
r = plan(files=["lib/small.py", "lib/big.py"])
check("a long whole file is refused before anything is billed, with its line count", r.get("ok") is False and r.get("billed_calls") == 0
      and r.get("files_need_ranges") == {"lib/big.py": 4000} and calls() == n, str(r)[:300])
r = plan(files=["lib/small.py", "lib/big.py:100-110"])
check("with a range it goes through", r.get("ok") is True and calls() == n + 1 and "100: line100 = 100" in open(SEEN).read())
reset(); r = plan(files=["lib/big.py"])
seen = open(SEEN).read()
check("still whole after being asked: only its first 120 lines are sent, and the plan text says so", r.get("ok") is True and "120: line120 = 120" in seen
      and "121: line121" not in seen and "Sent only in part" in r.get("present", ""), r.get("present", "")[-300:])
mcp._RANGES_ASKED.clear(); reset(); n = calls()
r = plan(files=["lib/big.py:1-3900"])
check("a range covering nearly the whole long file is refused like the whole file", r.get("files_need_ranges") == {"lib/big.py:1-3900": 4000} and calls() == n, str(r)[:200])
reset(); r = plan(files=["lib/big.py:1-900"])
seen = open(SEEN).read()
check("a range over 200 lines is cut to 200", "200: line200 = 200" in seen and "201: line201" not in seen and "lib/big.py:1-200" in r.get("present", ""))
open(PROJECT + "/lib/wide.py", "w").write("".join("x = '" + "y" * 150 + "'\n" for _ in range(110)))     # 110 lines, about 17,000 characters
reset(); r = plan(files=["lib/wide.py", "lib/small.py"]); seen = open(SEEN).read()
check("one entry is cut at the per-file limit, so the next one still fits", "[cut here: this entry was over the per-file limit]" in seen and "def small():" in seen
      and "Sent only in part" in r.get("present", ""), r.get("present", "")[-300:])
reset(); r = plan(files=["lib/wide.py", "lib/wide.py:1-50", "lib/wide.py:40-90", "lib/wide.py:60-110"])
check("the total sent to Claude is capped at 24,000 characters", mcp.PLAN_FILES_TOTAL_MAX == 24000 and "total size limit reached" in r.get("present", ""), r.get("present", "")[-300:])
os.remove(PROJECT + "/lib/wide.py")

print("ralph_plan: Claude may ask for more once, then must plan")
os.environ["AISTACK_TIER0"] = "lumo"
lumo_calls = []
def lumo_two(a):
    lumo_calls.append(a)
    if a.get("raw_prompt"):
        return {"ok": True, "plan": "REVISED DRAFT: " + "now names lib/small.py and the test command. " * 12, "lumo": "x"}
    return {"ok": True, "plan": "FIRST DRAFT: vague", "lumo": "x"}
real_lumo2, mcp.tool_lumo_consult = mcp.tool_lumo_consult, lumo_two
reset(); n = calls()
reply({"need": {"from_local_model": ["How is lib/small.py tested?", "Where is small() called?"], "for_lumo": "Name the real files; the draft is too vague."}})
mcp.RESEARCH_CALLS = mcp.RESEARCH_BUDGET
r = plan()
check("Claude's request for more comes back as questions, billed once, with no plan recorded", r.get("needs_more") is True and r.get("billed_calls") == 1
      and r.get("questions") == ["How is lib/small.py tested?", "Where is small() called?"] and not os.path.exists(STATE + "/plan-review.json")
      and not os.path.exists(STATE + "/plan/prd.json"), str(r)[:300])
check("Lumo is sent Claude's feedback with its own draft, and revises it", len(lumo_calls) == 2 and "too vague" in lumo_calls[1]["raw_prompt"]
      and "FIRST DRAFT" in lumo_calls[1]["raw_prompt"] and "revised" in r.get("lumo", ""), str(r.get("lumo")))
check("the questions get a fresh research budget", mcp.RESEARCH_CALLS == 0)
reply(GOOD)
r = plan(brief="small() is tested by tests/test_small.py with python3 -m unittest")
seen = open(SEEN).read()
check("the second call is the final attempt: no way to ask again, and it carries Lumo's revised draft", r.get("ok") is True and calls() == n + 2
      and "final attempt" in seen and '"need"' not in seen and "REVISED DRAFT" in seen and len(lumo_calls) == 2, str(r)[:200])
check("the plan text says two calls were billed", "2 billed calls for this plan" in r.get("present", ""), r.get("present", "")[-300:])
check("the pending request for more is cleared once the plan exists", not os.path.exists(STATE + "/plan/need.json"))
reset(); reply({"need": {"from_local_model": ["again?"], "for_lumo": ""}})
open(STATE + "/plan/need.json", "w").write(json.dumps({"questions": ["x"], "for_lumo": "", "draft": ""}))
r = plan()
check("asking again on the final attempt is not accepted as an answer", r.get("ok") is False and not r.get("needs_more") and "no plan" in r.get("problem", ""), str(r)[:200])
os.remove(STATE + "/plan/need.json")
mcp.tool_lumo_consult = real_lumo2; os.environ.pop("AISTACK_TIER0")

print("Lumo loop: runs here, through tamer, against this project")
seen_by_lumo, replies = [], ["I need two things.\nNEED: lib/small.py\nNEED: .env\nNEED: grep hunter2", "FINAL DRAFT: one task in lib/small.py"]
class Tamer(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self): self._send({"data": [{"id": "lumo"}]})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        seen_by_lumo.append({"auth": self.headers.get("Authorization"), "messages": body["messages"]})
        self._send({"choices": [{"message": {"role": "assistant", "content": replies[min(len(seen_by_lumo) - 1, len(replies) - 1)]}}]})
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Tamer); threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ.update(AISTACK_TAMER_URL=f"http://127.0.0.1:{srv.server_port}/v1", AISTACK_TAMER_KEY="tamer-key", AISTACK_LUMO_RESOLVER="keyword")
check("a pinned tamer is the only endpoint", list(mcp.tamer_endpoints()) == [(os.environ["AISTACK_TAMER_URL"], "tamer-key")])
r = mcp.tool_lumo_consult({"project_dir": PROJECT, "request": "add a thing", "files": ["lib/small.py"]})
check("Lumo is asked twice and its last answer is the draft", r.get("ok") and len(seen_by_lumo) == 2 and r["plan"].startswith("FINAL DRAFT") and r.get("lumo_finished") is True, str(r)[:300])
check("the tamer key is sent", seen_by_lumo[0]["auth"] == "Bearer tamer-key")
first, second = json.dumps(seen_by_lumo[0]["messages"]), seen_by_lumo[1]["messages"][-1]["content"]
check("the first request tells Lumo it may ask (NEED) and carries the listed file", "NEED" in first and "def small():" in first)
check("what Lumo asked for is answered from this project", "def small():" in second and r.get("lumo_asked_for") == ["lib/small.py", ".env", "grep hunter2"], second[:300])
check("a secret file is refused and its content never reaches Lumo", "hunter2" not in second.replace("grep hunter2", "") and "TOKEN=" not in second, second[:400])
seen_by_lumo.clear()
r = mcp.tool_lumo_consult({"project_dir": PROJECT, "request": "condense", "raw_prompt": "shorten this"})
check("the shorten request is one plain message with no loop", len(seen_by_lumo) == 1 and seen_by_lumo[0]["messages"] == [{"role": "user", "content": "shorten this"}] and r.get("ok"))
os.environ["AISTACK_TAMER_URL"] = "http://127.0.0.1:9/v1"
r = mcp.tool_lumo_consult({"project_dir": PROJECT, "request": "add a thing"})
check("a tamer that cannot be reached is reported, not raised", r.get("ok") is False and "Lumo is not available" in r.get("problem", ""), str(r)[:200])
for k in ("AISTACK_TAMER_URL", "AISTACK_TAMER_KEY", "AISTACK_LUMO_RESOLVER"): os.environ.pop(k)

print("Lumo order: this machine, then MacMiniM1, then the public endpoint")
port = srv.server_port
dead, live = "http://127.0.0.1:9/v1", f"http://127.0.0.1:{port}/v1"
looked = []
def key_of(name):
    def get():
        looked.append(name); return name + "-key"
    return get
def order(local, mini, public):
    looked.clear()
    mcp.TAMER_LOCAL_URL, mcp.TAMER_MINI_URL, mcp.TAMER_PUBLIC_URL = local, mini, public
    mcp.tamer_local_key, mcp.tamer_mini_key, mcp.tamer_public_key = key_of("local"), key_of("mini"), key_of("public")
    return mcp.tamer_endpoints()
first = next(order(live, live.replace("127.0.0.1", "localhost"), live + "/"))
check("a working local tamer is used and the others are not even looked up", first == (live, "local-key") and looked == ["local"], str(looked))
first = next(order(dead, live, live + "/"))
check("local down: MacMiniM1 is next, the public endpoint is not looked up", first == (live, "mini-key") and looked == ["local", "mini"], str(looked))
first = next(order(dead, dead, live))
check("local and MacMiniM1 down: the public endpoint is used", first == (live, "public-key") and looked == ["local", "mini", "public"], str(looked))
check("nothing answers: no endpoint", list(order(dead, dead, dead)) == [])
mcp.tamer_public_key = lambda: ""
check("no public key: the public endpoint is skipped, not called without one", list(mcp.tamer_endpoints()) == [])
srv.shutdown()

print("research tools: budget and guard")
subprocess.run(["git", "init", "-q"], cwd=PROJECT); subprocess.run(["git", "add", "-A", "-f"], cwd=PROJECT)
mcp.RESEARCH_CALLS = 0
A = {"project_dir": PROJECT}
r = mcp.tool_repo_tree(dict(A))
check("repo_tree shows the project in one call", r.get("ok") and "lib/big.py" in r["entries"] and "lib/small.py" in r["entries"] and r["calls_left"] == mcp.RESEARCH_BUDGET - 1, str(r)[:300])
check("repo_tree folds deeper directories", any(e.startswith("lib/") and "files below" in e for e in mcp.tool_repo_tree(dict(A, depth=1))["entries"]))
r = mcp.tool_repo_tree(dict(A, path="ansible"))
check("a path that does not exist is called a wrong guess", r.get("ok") is False and "your guess" in r.get("problem", ""))
r = mcp.tool_repo_read(dict(A, path="lib/big.py", start=10, end=12))
check("repo_read returns numbered lines, also from a big file", r.get("ok") and r["text"].splitlines() == ["10: line10 = 10", "11: line11 = 11", "12: line12 = 12"] and r["lines"] == "10-12 of 4000", str(r)[:200])
check("repo_read caps one call at 400 lines", len(mcp.tool_repo_read(dict(A, path="lib/big.py"))["text"].splitlines()) == 400)
check("repo_read refuses a secret file", mcp.tool_repo_read(dict(A, path=".env")).get("problem", "").endswith("denied by policy"))
r = mcp.tool_repo_grep(dict(A, pattern="def small|hunter2"))
check("repo_grep finds code and never returns a line from a secret file", r.get("ok") and any("lib/small.py:1:def small" in m for m in r["matches"]) and not any("hunter2" in m for m in r["matches"]), str(r)[:300])
used = mcp.RESEARCH_CALLS
for _ in range(mcp.RESEARCH_BUDGET - used): last = mcp.tool_repo_grep(dict(A, pattern="line1 "))
check("the last allowed calls warn that ralph_plan is next", "then call ralph_plan" in last.get("note", "") and last["calls_left"] == 0, str(last)[:200])
r = mcp.tool_repo_read(dict(A, path="lib/small.py"))
check("past the budget every research tool refuses and points to ralph_plan", r.get("ok") is False and "call ralph_plan now" in r.get("problem", "") and "text" not in r, str(r)[:200])
reset(); reply(GOOD); plan()
check("a finished plan gives a fresh budget", mcp.tool_repo_read(dict(A, path="lib/small.py")).get("ok") is True)
reset()

print("bridge: tool list")
names = [t["name"] for t in mcp.handle({"method": "tools/list"})["tools"]]
check("the aidev tools are listed and the old review tool is gone", {"ralph_plan", "ralph_update_task", "repo_tree", "repo_read", "repo_grep"} <= set(names) and "ralph_review_plan" not in names)

print("aidev dispatcher")
def aidev(args):
    cmd = (f"source {ROOT}/.zshrc_functions_ai 2>/dev/null; "
           '_aidev_stack() { print -r -- "stack args=$*"; }; '
           '_aidev_direct() { print -r -- "direct args=$*"; }; ' + args + '; print -r -- "aistack is: $(whence -w aistack 2>/dev/null)"')
    return subprocess.run(["zsh", "-c", cmd], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL).stdout.strip().splitlines()
out = aidev("aidev add a flag")
check("task words go to the one stack", out[:1] == ["stack args=add a flag"], str(out))
check("no arguments also starts the stack", aidev("aidev")[:1] == ["stack args="])
check("--direct goes to the direct session without the flag", aidev("aidev --direct fix it")[:1] == ["direct args=fix it"])
check("-p goes to the direct session with the flag", aidev("aidev -p 'fix it'")[:1] == ["direct args=-p fix it"])
check("any other flag goes to the direct session", aidev("aidev --model x")[:1] == ["direct args=--model x"])

print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
