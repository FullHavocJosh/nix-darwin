"""Tests for the tuios test stack (aidev_test.py, aidev_test_mcp.py) that need no tuios daemon, no model and no
network: task order, verify without a shell, the ask-human length cap, the test answer file, launcher scripts and
the research handoff. Uses the real stack's ralph_mcp.py from ~/.config/aistack (AISTACK_DIR overrides).
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-test/tests/test_aidev_test.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-test
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def project():
    p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))
    with open(os.path.join(p, "calc.py"), "w") as fh:
        fh.write("def add(a, b):\n    return a + b\n")
    subprocess.run(["git", "init", "-q"], cwd=p, check=False)
    subprocess.run(["git", "add", "."], cwd=p, check=False)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init"], cwd=p,
                   check=False)
    return p


def main():
    os.environ["AIDEV_TEST_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    a = load("aidev_test", os.path.join(ROOT, "aidev_test.py"))

    print("task order")
    prd = {"userStories": [{"id": "T3", "priority": 1, "dependsOn": ["T1"]}, {"id": "T1", "priority": 2},
                           {"id": "T2", "priority": 1}]}
    check("dependencies first, then priority", a.task_order(prd) == ["T2", "T1", "T3"], a.task_order(prd))
    cyc = {"userStories": [{"id": "A", "dependsOn": ["B"]}, {"id": "B", "dependsOn": ["A"]}]}
    check("a cycle still lists every task", sorted(a.task_order(cyc)) == ["A", "B"])

    print("verify without a shell")
    d = tempfile.mkdtemp()
    out = os.path.join(d, "v.txt")
    ok, _ = a.run_verify(["python3 -c 'import sys; sys.exit(0)'"], d, out)
    check("a passing command passes", ok)
    ok, text = a.run_verify(["python3 -c 'import sys; sys.exit(3)'"], d, out)
    check("a failing command fails, with its exit code in the output", not ok and "exit 3" in text)
    ok, text = a.run_verify(["echo hi ; false"], d, out)
    check("no shell: ';' is an argument, not an operator", ok and "hi ; false" in text, text)
    ok, _ = a.run_verify("python3 -c 'pass'", d, out)
    check("a single string counts as one command", ok)
    ok, text = a.run_verify(["no-such-binary-xyz"], d, out)
    check("a missing program fails", not ok and "exit 127" in text)
    check("the output is written to the file", open(out).read() == text)

    print("ask-human limits")
    q = "x" * 300
    check("a long question is cut to 160 bytes", len(a.short(q).encode()) <= 160)
    check("a short question is unchanged", a.short("Start the build?") == "Start the build?")
    check("multi-byte text is cut on a character boundary", a.short("é" * 200).encode().decode() is not None)

    print("test answer file")
    f = os.path.join(d, "answers.txt")
    with open(f, "w") as fh:
        fh.write("nonsense\nkeep planning\n")
    os.environ["AIDEV_TEST_FAKE_HUMAN"] = f
    got = a.fake_human("Start?", ["start", "keep planning"])
    check("the first line that is an option answers", got == "keep planning", got)
    check("that line is used up, others stay", open(f).read().split() == ["nonsense"])
    threading.Timer(1.0, lambda: open(f, "a").write("start\n")).start()
    t0 = time.time()
    got = a.fake_human("Start?", ["start", "keep planning"])
    check("it waits for an answer to arrive", got == "start" and time.time() - t0 >= 1.0)
    del os.environ["AIDEV_TEST_FAKE_HUMAN"]

    print("task prompt")
    story = {"id": "T1", "title": "Add subtract", "description": "In calc.py", "acceptanceCriteria": ["works"]}
    text = a.task_prompt({"name": "p", "description": "d"}, story, "python3 -m unittest", ["- Attempt 1 failed"])
    check("names the task, the checks and the earlier attempts",
          "Task T1" in text and "`python3 -m unittest`" in text and "Attempt 1 failed" in text)
    check("forbids commits", "No git commits" in text)

    print("launchers")
    p = project()
    run = a.Run(p, "20260101-000000")
    os.makedirs(run.dir, exist_ok=True)
    cfg = {"claude_settings": "/s.json", "claude_mcp": "/m.json"}
    body = a.claude_body(run, cfg, "plan", "SYSTEM", "first prompt", p)
    sid = run.data["panes"]["plan"]["session_id"]
    check("first start uses --session-id, a restart --resume, same id",
          f"--session-id {sid}" in body and f"--resume {sid}" in body)
    check("the first prompt is only on the first start", body.count("'first prompt'") == 1)
    check("advisor stays on for plan/review", "CLAUDE_ADVISOR=off" not in body)
    body2 = a.claude_body(run, cfg, "build-claude", "S", "go", p, advisor=False)
    check("the billed builder runs with advisor off", "export CLAUDE_ADVISOR=off" in body2)
    script = a.write_script(run, "plan", body)
    check("the launcher ends in a shell, so the pane survives the agent", open(script).read().rstrip().endswith(
        "exec zsh -i"))
    r = subprocess.run(["zsh", "-n", script], capture_output=True, text=True, check=False)
    check("the launcher is valid zsh", r.returncode == 0, r.stderr)
    check("session names are safe", a.session_name("/x/my repo.v2") == "aidev_test-my-repo-v2")
    check("HERDR_* never reaches tuios", not any(k.startswith("HERDR_") for k in a.TENV))
    print("session and workspaces")
    saved = {k: os.environ.get(k) for k in ("TUIOS_ENV", "TUIOS_SESSION", "AIDEV_TEST_OWN_SESSION")}
    os.environ.update(TUIOS_ENV="1", TUIOS_SESSION="dev_test-x")
    os.environ.pop("AIDEV_TEST_OWN_SESSION", None)
    check("inside tuios a run opens in the current session", a.start_session(p) == "dev_test-x")
    os.environ["AIDEV_TEST_OWN_SESSION"] = "1"
    check("AIDEV_TEST_OWN_SESSION=1 keeps a session of its own", a.start_session(p) == a.session_name(p))
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    real_windows = a.windows
    a.windows = lambda s: [{"workspace": 1}, {"workspace": 2}, {"workspace": 2}, {"workspace": 3}]
    r2 = a.Run(p, "20260101-000001")
    ws = r2.data.get("ws") if a.assign_workspaces(r2, "dev_test-x", own=False) is None else None
    check("the layers take the free workspaces in order",
          ws and ws["research"] == 4 and ws["driver"] == 9 and ws["build-claude"] == ws["build"] == 6, ws)
    a.windows = lambda s: [{"workspace": n} for n in range(1, 6)]
    check("too few free workspaces is refused", a.assign_workspaces(a.Run(p, "20260101-000002"), "s", own=False))
    a.windows = real_windows
    r3 = a.Run(p, "20260101-000003")
    a.assign_workspaces(r3, a.session_name(p), own=True)
    check("a session of its own uses the fixed numbers", r3.data["ws"] == a.WS_OWN)
    a.WS.clear()
    a.WS.update(a.WS_OWN)

    print("Lumo research")
    b, fl = a.parse_brief("thinking\nBRIEF:\ncalc.py adds.\nFILES:\n- calc.py:1-2\n2. `lib/x.py`\nnot a file\n")
    check("parse_brief splits the brief and the files", b == "calc.py adds." and fl == ["calc.py:1-2", "lib/x.py"],
          (b, fl))
    lr = a.Run(p, "20260101-000004")
    sid = lr.data["panes"].setdefault("research", {}).setdefault("session_id", "abc-123")
    os.makedirs(a.research_sessions(lr), exist_ok=True)
    sess = os.path.join(a.research_sessions(lr), f"2026-01-01T00-00-00-000Z_{sid}.jsonl")

    def say(eid, role, text):
        with open(sess, "a") as fh:
            fh.write(json.dumps({"type": "message", "id": eid,
                                 "message": {"role": role, "content": [{"type": "text", "text": text}]}}) + "\n")

    say("u1", "user", "REQUEST FROM THE USER: add subtract")
    say("a1", "assistant", "Let me look.\nNEED: calc.py")
    sent = []
    real = (a.agent_state, a.queue)
    a.agent_state = lambda s, n: "idle"
    a.queue = lambda s, n, t: sent.append(t) or True
    os.environ["RALPH_MCP_ROOTS"] = p
    ralph = a.load_ralph()
    a.lumo_step(lr, "s", ralph)
    check("a NEED line gets the file typed back",
          len(sent) == 1 and sent[0].startswith("Requested context:") and "def add" in sent[0], sent)
    a.lumo_step(lr, "s", ralph)
    check("the same reply is answered once", len(sent) == 1)
    say("u2", "user", sent[0] if sent else "Requested context:")
    say("a2", "assistant", "BRIEF:\ncalc.py has add only.\nFILES:\ncalc.py:1-2")
    a.lumo_step(lr, "s", ralph)
    bp = os.path.join(lr.plan_dir, "brief.md")
    text = open(bp).read() if os.path.isfile(bp) else ""
    check("BRIEF: becomes plan/brief.md with the request and the file",
          "add subtract" in text and "calc.py has add only" in text and "Requested context" not in text
          and "1: def add" in text, text[:300])
    lp = ralph.planner_lib()
    check("a line range is read, also written with a space",
          "1: def add" in a.resolve_need(ralph, lp, p, "calc.py:1-2")
          and "1: def add" in a.resolve_need(ralph, lp, p, "calc.py 1-2"))
    out = a.resolve_need(ralph, lp, p, 'grep -n "def add" calc.py | head -5')
    check("a shell-style grep is cut down to the pattern and the file", "[grep def add in calc.py]" in out
          and "calc.py:1:" in out, out)
    with open(os.path.join(p, ".env"), "w") as fh:
        fh.write("TOKEN=x\n")
    check("a range of a secret file is refused", "denied" in a.resolve_need(ralph, lp, p, ".env:1-1"))
    os.remove(os.path.join(p, ".env"))
    a.agent_state, a.queue = real
    lr.data["phase"] = "done"
    lr.save()

    print("run state")
    run.data["phase"] = "build"
    run.save()
    check("an unfinished run is picked up again", a.Run(p).id == "20260101-000000")
    run.data["phase"] = "done"
    run.save()
    check("a finished run is not", a.Run(p).id != "20260101-000000")

    print("research handoff (aidev_test_mcp.py)")
    os.environ["RALPH_MCP_ROOTS"] = p
    m = load("aidev_test_mcp", os.path.join(ROOT, "aidev_test_mcp.py"))
    res = m.tool_handoff({"project_dir": p, "request": "add subtract", "brief": "calc.py has add only",
                          "files": ["calc.py:1-2", ".env", "missing.py"]})
    brief = res.get("brief", "")
    check("handoff writes plan/brief.md in the test state dir",
          res.get("ok") and brief.startswith(os.environ["AIDEV_TEST_HOME"]) and os.path.isfile(brief), res)
    text = open(brief).read() if os.path.isfile(brief) else ""
    check("the brief has the request, the findings and the excerpt",
          "add subtract" in text and "calc.py has add only" in text and "1: def add(a, b):" in text)
    check("secrets and missing files are left out and listed", len(res.get("files_skipped", [])) == 2, res)
    check("handoff needs a request and a brief", not m.tool_handoff({"project_dir": p, "request": ""}).get("ok"))
    out = m.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = sorted(t["name"] for t in out["tools"])
    check("the research pane gets exactly these tools",
          names == ["handoff", "repo_grep", "repo_read", "repo_tree", "save_rfc"], names)
    os.environ["RALPH_MCP_ROOTS"] = "/nonexistent-root"
    m2 = load("aidev_test_mcp2", os.path.join(ROOT, "aidev_test_mcp.py"))
    msg = m2.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                     "params": {"name": "repo_tree", "arguments": {"project_dir": p}}})
    check("outside RALPH_MCP_ROOTS the tools refuse", msg.get("isError"), json.dumps(msg)[:200])

    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'all passed'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
