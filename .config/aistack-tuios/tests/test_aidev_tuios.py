"""Tests for aidev on tuios (aidev_tuios.py) that need no tuios daemon, no model and no network: task order, verify
without a shell, the ask-human length cap, the test answer file, launchers, sessions and workspaces, Claude's helpers
with a faked tuios, the Lumo pane and the Claude pane. Uses aistack's ralph_mcp.py from ~/.config/aistack
(AISTACK_DIR overrides).
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_aidev_tuios.py
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
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
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

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
    os.environ["AIDEV_TUIOS_FAKE_HUMAN"] = f
    got = a.fake_human("Start?", ["start", "keep planning"])
    check("the first line that is an option answers", got == "keep planning", got)
    check("that line is used up, others stay", open(f).read().split() == ["nonsense"])
    threading.Timer(1.0, lambda: open(f, "a").write("start\n")).start()
    t0 = time.time()
    got = a.fake_human("Start?", ["start", "keep planning"])
    check("it waits for an answer to arrive", got == "start" and time.time() - t0 >= 1.0)
    del os.environ["AIDEV_TUIOS_FAKE_HUMAN"]

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
    check("session names are safe", a.session_name("/x/my repo.v2") == "aidev-my-repo-v2")
    check("HERDR_* never reaches tuios", not any(k.startswith("HERDR_") for k in a.TENV))
    print("session and workspaces")
    saved = {k: os.environ.get(k) for k in ("TUIOS_ENV", "TUIOS_SESSION", "AIDEV_TUIOS_OWN_SESSION")}
    os.environ.update(TUIOS_ENV="1", TUIOS_SESSION="dev-x")
    os.environ.pop("AIDEV_TUIOS_OWN_SESSION", None)
    check("inside tuios a run opens in the current session", a.start_session(p) == "dev-x")
    os.environ["AIDEV_TUIOS_OWN_SESSION"] = "1"
    check("AIDEV_TUIOS_OWN_SESSION=1 keeps a session of its own", a.start_session(p) == a.session_name(p))
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    real_windows = a.windows
    a.windows = lambda s: [{"workspace": 1}, {"workspace": 2}, {"workspace": 2}, {"workspace": 3}]
    r2 = a.Run(p, "20260101-000001")
    ws = r2.data.get("ws") if a.assign_workspaces(r2, "dev-x", own=False) is None else None
    check("the layers take the free workspaces in order",
          ws and ws["claude"] == 4 and ws["lumo"] == 5 and ws["build-claude"] == ws["build"] == 6
          and "dev" not in ws, ws)
    a.windows = lambda s: [{"workspace": n} for n in range(1, 8)]
    check("too few free workspaces is refused", a.assign_workspaces(a.Run(p, "20260101-000002"), "s", own=False))
    a.windows = real_windows
    r3 = a.Run(p, "20260101-000003")
    a.assign_workspaces(r3, a.session_name(p), own=True)
    check("a session of its own uses the fixed numbers", r3.data["ws"] == a.WS_OWN)
    a.WS.clear()
    a.WS.update(a.WS_OWN)

    print("Claude's helpers")
    calls = []

    def fake_tuios(*args, timeout=60):
        calls.append(args)
        if args[0] == "send-agent-message":
            return 0, "message 7 queued for build (abcd1234)\n", ""
        return 0, "", ""

    real_t = (a.tuios, a.window_named, a.agent_state, a.tuios_json)
    a.tuios = fake_tuios
    a.window_named = lambda s, n: {"custom_name": n}
    check("the mail id is read from send-agent-message", a.mail_id("message 12 queued for build (x)") == "12")
    hr = a.Run(p, "20260101-000005")
    os.makedirs(hr.dir, exist_ok=True)
    hr.data.update(session="s", ws=dict(a.WS_OWN))
    ralph = a.load_ralph(p)
    plan_dir = ralph.plan_dir(p)
    check("aistack's plan dir is the run's", plan_dir == hr.plan_dir, (plan_dir, hr.plan_dir))
    os.makedirs(plan_dir, exist_ok=True)
    check("check-plan without files says so", a.cmd_check_plan(hr, []) == 1)
    a.wj(os.path.join(plan_dir, "prd.json"), {
        "name": "subtract", "title": "Add subtract", "description": "Adds sub to calc.py.",
        "userStories": [{"id": "T1", "title": "Add subtract", "description": "calc.py: def sub(a, b)",
                         "acceptanceCriteria": ["sub works"], "priority": 1, "passes": False, "dependsOn": []}]})
    a.wj(os.path.join(plan_dir, "verify.json"), {"T1": ["python3 -c 'import calc; assert calc.sub(3, 1) == 2'"]})
    check("a valid plan passes check-plan and gets PLAN.txt",
          a.cmd_check_plan(hr, []) == 0 and os.path.isfile(os.path.join(plan_dir, "PLAN.txt")))
    os.environ["AIDEV_TUIOS_WORKTREE_MODE"] = "none"
    check("worktree outside a main checkout works in the project",
          a.cmd_worktree(hr, []) == 0 and hr.data["work_dir"] == p)
    hr.data["builder"] = "build"
    check("send-task succeeds", a.cmd_send_task(hr, ["T1", "use the same style"]) == 0)
    sends = [c for c in calls if c[0] == "send-agent-message"]
    queues = [c for c in calls if c[0] == "queue"]
    check("the task is mailed to the builder", sends and "build" in sends[-1] and "task T1" in sends[-1], sends)
    check("the typed prompt names the mail to reply to", queues and "--reply-to 7" in queues[-1][-1], queues)
    tfile = open(os.path.join(hr.dir, "tasks", "T1.md")).read()
    check("Claude's note reaches the task file", "use the same style" in tfile)
    a.tuios_json = lambda *args, **kw: {"messages": [{"id": 7, "from": "claude (11111111)", "text": "task"},
                                                    {"id": 8, "from": "build (abcd1234)", "text": "done: sub"}]}
    a.agent_state = lambda s, n: "idle"
    check("wait-task takes the reply, then the checks fail while sub is missing",
          a.cmd_wait_task(hr, ["T1", "5"]) == 1 and hr.data["tasks"]["T1"]["status"] == "failed")
    with open(os.path.join(p, "calc.py"), "a") as fh:
        fh.write("\n\ndef sub(a, b):\n    return a - b\n")
    check("verify passes once the code is there",
          a.cmd_verify(hr, ["T1"]) == 0 and hr.data["tasks"]["T1"]["status"] == "verified")
    a.window_named = lambda s, n: None
    os.environ["AIDEV_TUIOS_FAKE_HUMAN"] = f
    with open(f, "w") as fh:
        fh.write("no\n")
    check("a billed builder needs the user's yes", a.cmd_builder(hr, ["claude"]) == 1
          and not any(c[0] == "start-agent" for c in calls))
    del os.environ["AIDEV_TUIOS_FAKE_HUMAN"]

    print("Lumo pane")
    lumo_dir = os.path.join(d, "pi-lumo")
    os.makedirs(lumo_dir, exist_ok=True)
    a.write_lumo_pi({"pi_lumo": lumo_dir}, ("http://127.0.0.1:3003/v1", "sekrit-key"))
    models = open(os.path.join(lumo_dir, "models.json")).read()
    check("the tamer key is in a 0600 file, not in models.json",
          os.stat(os.path.join(lumo_dir, "lumo.key")).st_mode & 0o777 == 0o600 and "sekrit-key" not in models
          and "!cat" in models)
    lsid = hr.data["panes"].setdefault("lumo", {}).setdefault("session_id", "lumo-1")
    os.makedirs(a.lumo_sessions(hr), exist_ok=True)
    sess = os.path.join(a.lumo_sessions(hr), f"2026-01-01T00-00-00-000Z_{lsid}.jsonl")

    def say(eid, role, text):
        with open(sess, "a") as fh:
            fh.write(json.dumps({"type": "message", "id": eid,
                                 "message": {"role": role, "content": [{"type": "text", "text": text}]}}) + "\n")

    say("u1", "user", "old question")
    say("a1", "assistant", "old answer")

    def lumo_turn(*args, timeout=60):
        calls.append(args)
        if args[0] == "ask-agent":
            say("u2", "user", args[-1])
            say("a2", "assistant", "Use X 2.0; see https://example.org")
        return 0, "", ""

    a.tuios = lumo_turn
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_ask_lumo(hr, ["which", "X?"])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("ask-lumo prints the new reply only", rc == 0 and "X 2.0" in printed and "old answer" not in printed,
          printed)
    asks = [c for c in calls if c[0] == "ask-agent"]
    check("the question goes to the lumo pane", asks and "lumo" in asks[-1] and asks[-1][-1] == "which X?", asks)

    print("Claude pane")
    ccfg = {"claude_settings": os.path.join(d, "s.json"), "claude_mcp": "/m.json",
            "claude_backbone": os.path.join(d, "b.json")}
    a.wj(ccfg["claude_settings"], {"hooks": {"x": 1}})
    body = a.claude_pane_body(hr, ccfg, "add subtract", True)
    check("the backbone runs with advisor off and knows its run",
          "export CLAUDE_ADVISOR=off" in body and f"AIDEV_TUIOS_RUN={hr.id}" in body)
    bs = json.load(open(ccfg["claude_backbone"]))
    check("its settings keep tuios's hooks and allow the helpers",
          bs.get("hooks") == {"x": 1} and any("aidev_tuios.py" in x for x in bs["permissions"]["allow"]))
    check("it runs in the default output style, not Advisor", bs.get("outputStyle") == "default")
    sysp = open(os.path.join(hr.dir, "bin", "claude.system.md")).read()
    check("its prompt names the helpers and has no placeholder left", "ask-lumo" in sysp and "@@" not in sysp)
    check("the builder holds less than Claude, so it cannot type into Claude's pane",
          set(a.GRANTS["build"].split(",")) < set(a.GRANTS["claude"].split(",")))
    a.tuios, a.window_named, a.agent_state, a.tuios_json = real_t
    hr.data["phase"] = "done"
    hr.save()

    print("run state")
    run.data["phase"] = "build"
    run.save()
    check("an unfinished run is picked up again", a.Run(p).id == "20260101-000000")
    run.data["phase"] = "done"
    run.save()
    check("a finished run is not", a.Run(p).id != "20260101-000000")

    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'all passed'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
