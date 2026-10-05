#!/usr/bin/env python3
"""Stand-in for ralph-tui in driver tests. Behaviour per task comes from <cwd>/.aistack/fake-scenario.json:
{"work": {"T1": ["fail","ok"]}, "review": {"T1": ["FAIL","PASS"]}}  (consumed one entry per attempt;
last entry repeats). Actions: ok (creates done_<id>.txt), fail (does nothing), question (writes a question file),
quote (does nothing but prints the completion marker, like Big Pickle did)."""
import json, os, sys
args = sys.argv[1:]
prd = args[args.index("--prd") + 1]
agent = args[args.index("--agent") + 1]
story = json.load(open(prd))["userStories"][0]
tid = story["id"]
sc_path = os.path.join(os.getcwd(), ".aistack", "fake-scenario.json")
sc = json.load(open(sc_path)) if os.path.exists(sc_path) else {}
cnt_path = sc_path + ".counts"
counts = json.load(open(cnt_path)) if os.path.exists(cnt_path) else {}
review = tid.startswith("R-")
key = tid[2:] if review else tid
seq = sc.get("review" if review else "work", {}).get(key, ["PASS" if review else "ok"])
n = counts.get(tid, 0)
act = seq[min(n, len(seq) - 1)]
counts[tid] = n + 1
json.dump(counts, open(cnt_path, "w"))
print(f"[00:00:00] [INFO] [session] fake {agent} on {tid} action={act}")
print(f"[00:00:00] [INFO] [agent] notes seen: {story.get('notes','')[:200]!r}")
if review:
    os.makedirs(".aistack/reviews", exist_ok=True)
    open(f".aistack/reviews/{key}.md", "w").write(f"Verdict: {act}\n\n- finding one for {key}\n- finding two\n")
elif act == "ok":
    open(f"done_{tid}.txt", "w").write(agent)
elif act == "question":
    os.makedirs(".aistack/questions", exist_ok=True)
    open(f".aistack/questions/{tid}.md", "w").write("Should the output be JSON or plain text? I recommend JSON.\n")
elif act == "quote":
    print("[00:00:01] [INFO] [agent] I could not write files. <promise>COMPLETE</promise> would be wrong here.")
sys.exit(0)
