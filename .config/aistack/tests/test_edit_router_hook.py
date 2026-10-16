"""Tests for edit_router_hook.py (third hand-edited file in one request goes to local_edit / oczen_edit).
Fake transcripts, a scratch repo with a linked worktree, a temporary HOME; no Claude, no model.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_edit_router_hook.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(os.path.dirname(HERE), "edit_router_hook.py")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="edit-router-"))
MAIN, WT, HOME = T + "/main", T + "/wt", T + "/home"
os.makedirs(MAIN)
os.makedirs(HOME)
subprocess.run(f"cd {MAIN} && git init -q && touch x && git add x && git -c user.name=t -c user.email=t@t commit -qm i"
               f" && git worktree add -q -b w {WT}", shell=True)
MODEL = T + "/model.gguf"
open(MODEL, "w").write("stub")


def entry_user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def entry_tool(name, inp, tid):
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def entry_result(tid, error=False):
    return {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "is_error": error, "content": "x"}]}}


def run(entries, path, model=True, key=False, tool="Edit", env=None, state=None, session="s1", tid="now"):
    tr = T + "/transcript.jsonl"
    with open(tr, "w") as f:
        f.writelines(json.dumps(e) + "\n" for e in entries)
    e = {k: v for k, v in os.environ.items() if k not in ("OPENCODE_ZEN_API_KEY", "CLAUDE_EDIT_ROUTER")}
    e.update(HOME=HOME, LOCAL_EDIT_MODEL_FILE=MODEL if model else T + "/missing.gguf",
             CLAUDE_EDIT_ROUTER_STATE=state or tempfile.mkdtemp(dir=T), **(env or {}))
    if key:
        e["OPENCODE_ZEN_API_KEY"] = "k"
    inp = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"file_path": path}, "tool_use_id": tid,
           "session_id": session,
           "transcript_path": tr, "cwd": WT}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(inp), capture_output=True, text=True, env=e)
    out = p.stdout.strip()
    return json.loads(out)["hookSpecificOutput"] if out else None


def edits(*names, start=0):
    out = []
    for i, n in enumerate(names):
        out += [entry_tool("Edit", {"file_path": f"{WT}/{n}"}, f"e{start + i}"), entry_result(f"e{start + i}")]
    return out


print("counting")
check("first and second hand-edited files are allowed", run([entry_user("go")] + edits("a.py"), f"{WT}/b.py") is None)
d = run([entry_user("go")] + edits("a.py", "b.py"), f"{WT}/c.py")
check("the third file is refused, pointing to local_edit", d and d["permissionDecision"] == "deny" and "local_edit" in d["permissionDecisionReason"], d)
check("more edits to a file already edited stay allowed", run([entry_user("go")] + edits("a.py", "b.py"), f"{WT}/a.py") is None)
check("a new user request starts a new count", run([entry_user("one")] + edits("a.py", "b.py") + [entry_user("two")], f"{WT}/c.py") is None)
check("Write is exempt (the whole file is already in the call)", run([entry_user("go")] + edits("a.py", "b.py"), f"{WT}/new.py", tool="Write") is None)
writes = [entry_tool("Write", {"file_path": f"{WT}/w{i}.py"}, f"w{i}") for i in range(3)] + [entry_result(f"w{i}") for i in range(3)]
check("earlier Writes do not count toward the limit", run([entry_user("go")] + writes + edits("a.py"), f"{WT}/b.py") is None)
check("editing a file Written in this request is allowed", run([entry_user("go")] + writes + edits("a.py", "b.py"), f"{WT}/w1.py") is None)
check("Edit still counts after Writes", (run([entry_user("go")] + writes + edits("a.py", "b.py"), f"{WT}/c.py") or {}).get("permissionDecision") == "deny")
check("the current call itself is not counted twice",
      run([entry_user("go")] + edits("a.py") + [entry_tool("Edit", {"file_path": f"{WT}/b.py"}, "now")], f"{WT}/b.py") is None)

print("parallel calls (not in the transcript yet)")
st = tempfile.mkdtemp(dir=T)
prompt = [{"type": "user", "uuid": "u1", "message": {"role": "user", "content": "go"}}]
r1 = run(prompt, f"{WT}/p1.py", state=st, tid="t1")
r2 = run(prompt, f"{WT}/p2.py", state=st, tid="t2")
r3 = run(prompt, f"{WT}/p3.py", state=st, tid="t3")
check("third file in one response is refused from the hook's own record", r1 is None and r2 is None and (r3 or {}).get("permissionDecision") == "deny", (r1, r2, r3))
newprompt = prompt + [{"type": "user", "uuid": "u2", "message": {"role": "user", "content": "next"}}]
check("a new request resets the record", run(newprompt, f"{WT}/p3.py", state=st, tid="t4") is None)
check("another session has its own record", run(prompt, f"{WT}/p9.py", state=st, session="s2", tid="t5") is None)

print("exceptions")
check("allowed when no delegate exists (no 30B, no Zen key)", run([entry_user("go")] + edits("a.py", "b.py"), f"{WT}/c.py", model=False) is None)
d = run([entry_user("go")] + edits("a.py", "b.py"), f"{WT}/c.py", model=False, key=True)
check("only Big Pickle available: refused, pointing to oczen_edit only", d and "oczen_edit" in d["permissionDecisionReason"] and "local_edit instead" not in d["permissionDecisionReason"].split("Prefer")[0], d)
check("allowed outside a linked worktree (main checkout)", run([entry_user("go")] + edits("a.py", "b.py"), f"{MAIN}/c.py") is None)
failed = [entry_tool("mcp__local-edit__local_edit", {"instruction": "x", "files": ["c.py"]}, "d1"), entry_result("d1", error=True)]
check("allowed after a failed delegation in this request", run([entry_user("go")] + edits("a.py", "b.py") + failed, f"{WT}/c.py") is None)
ok = [entry_tool("mcp__local-edit__local_edit", {"instruction": "x", "files": ["c.py"]}, "d2"), entry_result("d2", error=False)]
ok = [entry_tool("mcp__local-edit__local_edit", {"instruction": "x", "files": ["z.py"]}, "d2"), entry_result("d2", error=False)]
check("a successful delegation does not unlock other files", (run([entry_user("go")] + edits("a.py", "b.py") + ok, f"{WT}/c.py") or {}).get("permissionDecision") == "deny")
check("fixing up a delegated file (absolute or relative path) is allowed",
      run([entry_user("go")] + edits("a.py", "b.py") + [entry_tool("mcp__local-edit__local_edit", {"instruction": "x", "files": [f"{WT}/d.py", "e.py"]}, "d3"), entry_result("d3")], f"{WT}/d.py") is None
      and run([entry_user("go")] + edits("a.py", "b.py") + [entry_tool("mcp__local-edit__local_edit", {"instruction": "x", "files": [f"{WT}/d.py", "e.py"]}, "d4"), entry_result("d4")], f"{WT}/e.py") is None)
single = [entry_tool("mcp__local-edit__local_edit", {"instruction": "x", "file": "f.py", "start_line": 1, "end_line": 2}, "d5"), entry_result("d5")]
check("fixing up the single file a delegation edited is allowed", run([entry_user("go")] + edits("a.py", "b.py") + single, f"{WT}/f.py") is None)
check("CLAUDE_EDIT_ROUTER=off disables it", run([entry_user("go")] + edits("a.py", "b.py"), f"{WT}/c.py", env={"CLAUDE_EDIT_ROUTER": "off"}) is None)
check("a broken transcript fails open", run([], f"{WT}/c.py") is None)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
