"""Tests for aidev's planning path: ralph_plan in ralph_mcp.py (Claude writes the plan) and the aidev dispatcher.
Claude is replaced by AISTACK_PLAN_CMD (a shell command that prints a canned reply); nothing here is billed.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_plan.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

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
r = plan(files=["lib/small.py", "lib/big.py:10-12", "lib/big.py", ".env", "../outside.py"], draft="T1: do it")
check("ok with a plan_hash", r.get("ok") is True and r.get("plan_hash"), str(r)[:300])
check("one billed call reported", r.get("billed_calls") == 1 and calls() == 1)
check("tasks and notes returned", r.get("tasks", [{}])[0].get("id") == "T1" and r.get("notes") == ["assumed python3"])
prd, verify = json.load(open(STATE + "/plan/prd.json")), json.load(open(STATE + "/plan/verify.json"))
check("passes is forced to false", prd["userStories"][0]["passes"] is False)
check("a single verify command becomes a list", verify["T1"] == ["python3 -m unittest tests.test_thing"])
check("the saved plan validates", mcp.tool_validate({"project_dir": PROJECT}).get("plan_hash") == r.get("plan_hash"))
check("ralph_run's review gate is satisfied", json.load(open(STATE + "/plan-review.json")).get("verdict") == "PLANNED")
check("whole file and line range sent", r.get("files_sent") == ["lib/small.py", "lib/big.py:10-12"], str(r.get("files_sent")))
sk = r.get("files_skipped", {})
check("oversized whole file skipped", "larger than" in sk.get("lib/big.py", ""), str(sk))
check("secret file refused", sk.get(".env") == "denied by policy", str(sk))
check("path outside the project refused", sk.get("../outside.py") == "outside the project", str(sk))
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
check("an invalid plan still blocks a second billed call", plan().get("already_planned") is True)
reset(); n = calls(); reply("I could not do this.")
r = plan()
check("no JSON: ok false, raw output kept", r.get("ok") is False and os.path.exists(STATE + "/plan/claude-plan.raw.txt") and calls() == n + 1)
check("no JSON: no plan record is written", not os.path.exists(STATE + "/plan-review.json"))
check("empty request refused without a call", mcp.tool_plan({"project_dir": PROJECT, "request": " ", "brief": "x"}).get("ok") is False and calls() == n + 1)
reset(); reply(GOOD)
r = plan(brief="b" * 20000)
check("an oversized brief is cut and reported", r.get("truncated") == ["brief"] and len(open(SEEN).read()) < 20000, str(r.get("truncated")))

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

print("bridge: tool list")
names = [t["name"] for t in mcp.handle({"method": "tools/list"})["tools"]]
check("ralph_plan and ralph_update_task are listed and ralph_review_plan is still there", {"ralph_plan", "ralph_update_task", "ralph_review_plan"} <= set(names))

print("aidev dispatcher")
def aidev(args):
    cmd = (f"source {ROOT}/.zshrc_functions_ai 2>/dev/null; "
           'aistack_func() { print -r -- "stack mode=${_AISTACK_MODE:-unset} args=$*"; }; '
           '_aidev_direct() { print -r -- "direct args=$*"; }; ' + args + '; print -r -- "after=${_AISTACK_MODE:-unset}"')
    return subprocess.run(["zsh", "-c", cmd], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL).stdout.strip().splitlines()
out = aidev("aidev add a flag")
check("task words go to the stack in dev mode", out[:1] == ["stack mode=dev args=add a flag"], str(out))
check("the mode does not leak into the shell", out[-1:] == ["after=unset"], str(out))
check("no arguments also starts the stack", aidev("aidev")[:1] == ["stack mode=dev args="])
check("--direct goes to the direct session without the flag", aidev("aidev --direct fix it")[:1] == ["direct args=fix it"])
check("-p goes to the direct session with the flag", aidev("aidev -p 'fix it'")[:1] == ["direct args=-p fix it"])
check("any other flag goes to the direct session", aidev("aidev --model x")[:1] == ["direct args=--model x"])

print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
