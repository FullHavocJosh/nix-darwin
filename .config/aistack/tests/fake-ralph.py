#!/usr/bin/env python3
"""Stand-in for ralph-tui in driver tests. Behaviour per task comes from $AISTACK_STATE_DIR/fake-scenario.json:
{"work": {"T1": ["fail","ok"]}, "review": {"T1": ["FAIL","PASS"]}}  (consumed one entry per attempt;
last entry repeats). Actions: ok (creates done_<id>.txt), fail (does nothing), question (writes a question file),
quote (does nothing but prints the completion marker, like Big Pickle did).
Like the real thing it starts in the state dir (ralph's cwd, recorded in fake-cwd.txt) and then, like the agent
wrappers, moves to $AISTACK_WORKDIR to do the work. Questions and reviews go to the state dir, never the repo."""
import json
import os
import sys

args = sys.argv[1:]
prd = args[args.index("--prd") + 1]
agent = args[args.index("--agent") + 1]
state = os.environ["AISTACK_STATE_DIR"]
with open(os.path.join(state, "fake-cwd.txt"), "a") as f:
    f.write(os.getcwd() + "\n")
os.chdir(os.environ["AISTACK_WORKDIR"])
story = json.load(open(prd))["userStories"][0]
tid = story["id"]
sc_path = os.path.join(state, "fake-scenario.json")
sc = json.load(open(sc_path)) if os.path.exists(sc_path) else {}
cnt_path = sc_path + ".counts"
counts = json.load(open(cnt_path)) if os.path.exists(cnt_path) else {}
review = tid.startswith("R-")
key = tid[2:] if review else tid
n = counts.get(tid, 0)
counts[tid] = n + 1
json.dump(counts, open(cnt_path, "w"))
if tid == "R-batch":
    # one review call for all tasks: the report path is in the acceptance criterion ("<path> exists and ...")
    report = story["acceptanceCriteria"][0].split(" exists and")[0]
    plan = json.load(open(os.path.join(state, "plan", "prd.json")))["userStories"]
    verdict = {}
    for st in plan:
        sq = sc.get("review", {}).get(st["id"], ["PASS"])
        verdict[st["id"]] = sq[min(n, len(sq) - 1)]
    print(f"[00:00:00] [INFO] [session] fake {agent} batch review #{n + 1}: {verdict}")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    overall = "FAIL" if "FAIL" in verdict.values() else "PASS"
    open(report, "w").write(f"Verdict: {overall}\n" + "".join(f"Task {t}: {v}\n" for t, v in verdict.items())
                            + "".join(f"\n- finding one for {t}\n- finding two\n" for t in verdict))
    sys.exit(0)
seq = sc.get("review" if review else "work", {}).get(key, ["PASS" if review else "ok"])
act = seq[min(n, len(seq) - 1)]
print(f"[00:00:00] [INFO] [session] fake {agent} on {tid} action={act}")
print(f"[00:00:00] [INFO] [agent] notes seen: {story.get('notes','')[:200]!r}")
if review:
    os.makedirs(os.path.join(state, "reviews"), exist_ok=True)
    open(os.path.join(state, "reviews", f"{key}.md"), "w").write(f"Verdict: {act}\n\n- finding one for {key}\n- finding two\n")
elif act == "ok":
    open(f"done_{tid}.txt", "w").write(agent)
elif act == "question":
    os.makedirs(os.path.join(state, "questions"), exist_ok=True)
    open(os.path.join(state, "questions", f"{tid}.md"), "w").write("Should the output be JSON or plain text? I recommend JSON.\n")
elif act == "quote":
    print("[00:00:01] [INFO] [agent] I could not write files. <promise>COMPLETE</promise> would be wrong here.")
sys.exit(0)
