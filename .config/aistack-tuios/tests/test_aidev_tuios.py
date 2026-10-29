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
    os.environ.pop("AIDEV_TUIOS_BUILDER", None)  # the suite tests cmd_edit's refusal itself, whatever pane runs it
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
    check("forbids destructive git", "never run git checkout" in text)

    print("builder git guard, snapshots and lost changes")
    gp = project()
    gr = a.Run(gp, "20260101-000020")
    os.makedirs(gr.dir, exist_ok=True)
    guard = a.write_git_guard(gr)
    check("the guard is executable", os.access(guard, os.X_OK))

    def gg(*args):
        return subprocess.run([guard, *args], cwd=gp, capture_output=True, text=True, check=False)

    for args in (("checkout", "--", "calc.py"), ("stash",), ("commit", "-m", "x"), ("-C", gp, "reset", "--hard")):
        r = gg(*args)
        check(f"the guard blocks git {' '.join(args)}", r.returncode == 1 and
              f"git {args[2] if args[0] == '-C' else args[0]} is blocked in the builder panes: the planner owns git. "
              "Edit files and run the checks only." in r.stderr, r.stderr)
    check("the guard passes git status through", gg("status", "--short").returncode == 0)
    check("the guard passes checkout of a branch through", gg("checkout", "-b", "ok").returncode == 0)
    gr.data["work_dir"] = gp
    with open(os.path.join(gp, "calc.py"), "a") as fh:
        fh.write("def sub(a, b):\n    return a - b\n")
    with open(os.path.join(gp, "new.txt"), "w") as fh:
        fh.write("x\n")
    sp = a.snapshot_work(gr, "T1-attempt1-before")
    check("snapshot_work writes the patch and the untracked files",
          "+def sub" in open(sp).read() and
          "new.txt" in open(os.path.join(gr.dir, "snapshots", "T1-attempt1-before.untracked")).read())
    check("lost_changes reports nothing while the diff holds", a.lost_changes(gr, "T1-attempt1-before") == [])
    with open(os.path.join(gp, "calc.py"), "w") as fh:
        fh.write("def add(a, b):\n    return a + b\n")
    check("lost_changes reports a file whose added lines dropped",
          a.lost_changes(gr, "T1-attempt1-before") == [("calc.py", 2, 0)], a.lost_changes(gr, "T1-attempt1-before"))

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
    body2 = a.claude_body(run, cfg, "build-billed", "S", "go", p, advisor=False)
    check("the billed builder runs with advisor off", "export CLAUDE_ADVISOR=off" in body2)
    script = a.write_script(run, "plan", body)
    check("the launcher ends in a shell, so the pane survives the agent", open(script).read().rstrip().endswith(
        "exec zsh -i"))
    check("the launcher pins the caller's PATH (nix-darwin's zshenv resets it)",
          f"export PATH={a.shlex.quote(os.environ['PATH'])}\n" in open(script).read())
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
    check("without an nvim window plan, research and every builder get workspace 4",
          ws and ws[a.PLAN] == 4 and ws[a.RESEARCH] == ws["build-local"] == ws["build-billed"] == 4 and "dev" not in ws, ws)
    a.windows = lambda s: [{"workspace": 1, "custom_name": "nvim"}, {"workspace": 3}]
    r4 = a.Run(p, "20260101-000004")
    ws = r4.data.get("ws") if a.assign_workspaces(r4, "dev-x", own=False) is None else None
    check("in the dev layout Claude joins nvim's workspace, Lumo and the builders all use the same workspace",
          ws and ws[a.PLAN] == ws[a.RESEARCH] == ws["build-local"] == ws["build-free"] == ws["build-billed"] == 1, ws)
    a.windows = lambda s: [{"workspace": n} for n in range(1, 10)]
    check("with every workspace used and no nvim window the run is refused", a.assign_workspaces(a.Run(p, "20260101-000002"), "s", own=False))
    a.windows = lambda s: [{"workspace": 1, "custom_name": "nvim"}] + [{"workspace": n} for n in range(2, 10)]
    check("nvim workspace alone is enough", a.assign_workspaces(a.Run(p, "20260101-000007"), "s", own=False) is None)
    a.windows = real_windows
    real_run, real_platform = a.subprocess.run, a.sys.platform
    saved_notify = os.environ.pop("AIDEV_TUIOS_NO_NOTIFY", None)
    notified = []
    a.subprocess.run = lambda argv, **kw: notified.append(argv)
    a.sys.platform = "darwin"
    try:
        a.notify_local("x")
        check("notify_local runs osascript with the text last",
              len(notified) == 1 and notified[0][0] == "osascript" and notified[0][-1] == "x", notified)
        os.environ["AIDEV_TUIOS_NO_NOTIFY"] = "1"
        a.notify_local("y")
        check("AIDEV_TUIOS_NO_NOTIFY=1 silences notify_local", len(notified) == 1, notified)
    finally:
        a.subprocess.run, a.sys.platform = real_run, real_platform
        os.environ.pop("AIDEV_TUIOS_NO_NOTIFY", None)
        if saved_notify is not None:
            os.environ["AIDEV_TUIOS_NO_NOTIFY"] = saved_notify
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
        if args[0] == "capture-pane":
            return 0, "New session started\n", ""
        return 0, "", ""

    real_t = (a.tuios, a.window_named, a.agent_state, a.tuios_json)
    a.tuios = fake_tuios
    a.window_named = lambda s, n: {"custom_name": n}
    check("the mail id is read from send-agent-message", a.mail_id("message 12 queued for build (x)") == "12")
    hr = a.Run(p, "20260101-000005")
    os.makedirs(hr.dir, exist_ok=True)
    hr.data.update(session="s", ws=dict(a.WS_OWN))
    ralph = a.load_ralph(p, hr)
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
    print("builder reset")
    real_sleep, real_tuios = a.time.sleep, a.tuios
    a.time.sleep = lambda s: None
    reset_calls, captured = [], ["New session started\n"]

    def reset_tuios(*args, timeout=60):
        reset_calls.append(args)
        if args[0] == "capture-pane":
            return 0, captured[0], ""
        if args[0] == "send-agent-message":
            return 0, "message 21 queued for build (abcd1234)\n", ""
        return 0, "", ""

    def reset_texts():
        return [c[-1] for c in reset_calls if c[0] == "send-text"]

    def reset_before_mail():
        kinds = [c[0] for c in reset_calls]
        return ("send-text" in kinds and "send-agent-message" in kinds
                and kinds.index("send-text") < kinds.index("send-agent-message"))

    def mailed():
        return any(c[0] == "send-agent-message" for c in reset_calls)

    a.tuios = reset_tuios
    hr.data["builder"] = "build-local"
    os.environ.pop("AIDEV_NO_RESET", None)
    a.agent_state = lambda s, n: "idle"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_send_task(hr, ["T1"])
    finally:
        sys.stdout = real_stdout
    check("send-task resets an idle builder with /new, before mailing the task",
          rc == 0 and reset_texts() == ["/new"] and reset_before_mail(), reset_calls)
    reset_calls.clear()
    a.agent_state = lambda s, n: "working"
    a.RESET_WAIT = 0
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_send_task(hr, ["T1"])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("a working builder is not reset and the task is refused",
          rc == 1 and not mailed() and "refusing" in printed, (reset_calls, printed))
    reset_calls.clear()
    captured[0] = "still working...\n"
    a.agent_state = lambda s, n: "none"
    a.RESET_WAIT = 0
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_send_task(hr, ["T1"])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("an unconfirmed reset refuses to send the task and mails nothing",
          rc == 1 and not mailed() and "refusing" in printed and len([c for c in reset_calls if c[0] == "capture-pane"]) == 10, (reset_calls, printed))
    reset_calls.clear()
    captured[0] = "context 0.0%/128k tokens\n"
    hr.data["builder"] = "build-billed"
    a.agent_state = lambda s, n: "done"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_send_task(hr, ["T1"])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("a done Claude builder is cleared with /clear and 0.0% context confirms it",
          rc == 0 and reset_texts() == ["/clear"] and "reset not confirmed" not in printed, (reset_calls, printed))
    reset_calls.clear()
    hr.data["builder"] = "build-local"
    a.agent_state = lambda s, n: "idle"
    os.environ["AIDEV_NO_RESET"] = "1"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_send_task(hr, ["T1"])
    finally:
        sys.stdout = real_stdout
        os.environ.pop("AIDEV_NO_RESET", None)
    check("AIDEV_NO_RESET=1 skips the reset and still mails the task",
          rc == 0 and not reset_texts() and mailed(), reset_calls)
    reset_calls.clear()
    captured[0] = "80.0%/33k (auto)\n"
    hr.data["builder"] = "build-billed"
    a.agent_state = lambda s, n: "none"
    a.RESET_WAIT = 0
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_send_task(hr, ["T1"])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("80.0% context does not confirm the reset",
          rc == 1 and "refusing" in printed and len([c for c in reset_calls if c[0] == "capture-pane"]) == 10, (reset_calls, printed))
    reset_calls.clear()
    captured[0] = "new session ses_abc\n"
    hr.data["builder"] = "build-local"
    a.agent_state = lambda s, n: "none"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_send_task(hr, ["T1"])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("a lowercase 'new session' confirms the reset",
          rc == 0 and "reset not confirmed" not in printed, (reset_calls, printed))
    a.tuios, a.time.sleep, a.agent_state = real_tuios, real_sleep, (lambda s, n: "idle")
    hr.data["builder"] = "build-local"
    check("send-task succeeds", a.cmd_send_task(hr, ["T1", "use the same style"]) == 0)
    sends = [c for c in calls if c[0] == "send-agent-message"]
    queues = [c for c in calls if c[0] == "queue"]
    check("the task is mailed to the builder", sends and "build-local" in sends[-1] and "task T1" in sends[-1], sends)
    check("the typed prompt names the mail to reply to", queues and "--reply-to 7" in queues[-1][-1], queues)
    tfile = open(os.path.join(hr.dir, "tasks", "T1.md")).read()
    check("Claude's note reaches the task file", "use the same style" in tfile)
    a.tuios_json = lambda *args, **kw: {"messages": [{"id": 7, "from": "plan (11111111)", "text": "task"},
                                                    {"id": 8, "from": "build-local (abcd1234)", "text": "done: sub"}]}
    a.agent_state = lambda s, n: "idle"
    check("wait-task takes the reply, then the checks fail while sub is missing",
          a.cmd_wait_task(hr, ["T1", "5"]) == 1 and hr.data["tasks"]["T1"]["status"] == "failed")
    with open(os.path.join(p, "calc.py"), "a") as fh:
        fh.write("\n\ndef sub(a, b):\n    return a - b\n")
    check("verify passes once the code is there",
          a.cmd_verify(hr, ["T1"]) == 0 and hr.data["tasks"]["T1"]["status"] == "verified")
    mail = {"messages": [{"id": 9, "from": "build-local (abcd1234)", "text": "blocked: need the spec"}]}
    a.tuios_json = lambda *args, **kw: mail if "--unread" in args else {}
    hr.save()
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_watch(hr, ["5"])
        printed = sys.stdout.getvalue()
        hr.data["tasks"]["T1"]["status"] = "sent"
        hr.save()
        rc2 = a.cmd_watch(hr, ["1"])
    finally:
        sys.stdout = real_stdout
    check("watch prints new mail and exits 0", rc == 0 and "blocked: need the spec" in printed, printed)
    check("watch leaves the builder's mail to wait-task while a task waits on it", rc2 == 3)
    hr.data["tasks"]["T1"]["status"] = "verified"
    hr.save()
    a.window_named = lambda s, n: None
    os.environ["AIDEV_TUIOS_FAKE_HUMAN"] = f
    with open(f, "w") as fh:
        fh.write("no\n")
    check("a billed builder needs the user's yes", a.cmd_builder(hr, ["claude"]) == 1
          and not any(c[0] == "start-agent" for c in calls))
    del os.environ["AIDEV_TUIOS_FAKE_HUMAN"]

    print("merged")
    real_sleep_m, real_tuios_m, real_wn_m, real_as_m = a.time.sleep, a.tuios, a.window_named, a.agent_state
    a.time.sleep = lambda s: None
    merged_calls, merged_captured = [], ["New session started\n"]

    def merged_tuios(*args, timeout=60):
        merged_calls.append(args)
        if args[0] == "capture-pane":
            return 0, merged_captured[0], ""
        if args[0] == "send-agent-message":
            return 0, "message 99 queued for build (abcd1234)\n", ""
        return 0, "", ""

    def merged_send_texts():
        return [c for c in merged_calls if c[0] == "send-text"]

    a.tuios = merged_tuios
    os.environ.pop("AIDEV_NO_RESET", None)

    # Case 1
    mr = a.Run(p, "20260101-000010")
    mr.data.update(phase="open", session="s", ws=dict(a.WS_OWN), panes={a.PLAN: {"cwd": p}, a.RESEARCH: {"cwd": p}}, tasks={"T1": {"status": "verified"}, "T2": {"status": "sent"}})
    mr.save()
    a.window_named = lambda s, n: {"custom_name": n, "cwd": p} if n in (a.PLAN, a.RESEARCH, "build-local", "build-billed", "build-free") else None
    a.agent_state = lambda s, n: "idle"
    merged_calls.clear()
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_merged(mr, [])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("merged refuses while tasks not verified", rc == 1 and "tasks not verified yet: T2" in printed and not merged_send_texts(), (rc, printed))

    # Case 2
    mr2 = a.Run(p, "20260101-000011")
    mr2.data.update(phase="open", session="s", ws=dict(a.WS_OWN), panes={a.PLAN: {"cwd": p}, a.RESEARCH: {"cwd": p}}, tasks={"T1": {"status": "verified"}, "T2": {"status": "verified"}}, builder="build-local", work_dir=p)
    mr2.save()
    def merged_win2(s, n):
        if n == a.PLAN: return {"custom_name": n, "cwd": p}
        if n == a.RESEARCH: return {"custom_name": n, "cwd": p}
        if n == "build-local": return {"custom_name": n, "cwd": p}
        return None
    a.window_named = merged_win2
    def merged_state2(s, n):
        if n == a.RESEARCH: return "idle"
        if n == "build-local": return "done"
        return "idle"
    a.agent_state = merged_state2
    merged_calls.clear()
    merged_captured[0] = "context 0.0%/128k tokens\n"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_merged(mr2, [])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    texts = [c for c in merged_calls if c[0] == "send-text"]
    check("merged resets Lumo and builder when all verified, not Claude", rc == 0 and "compact" in printed and len([t for t in texts if len(t) > 4 and t[4] == a.RESEARCH and t[5] == "/new"]) >= 1 and len([t for t in texts if len(t) > 4 and t[4] == "build-local" and t[5] == "/new"]) >= 1, (printed, texts))

    # Case 3
    mr3 = a.Run(p, "20260101-000012")
    mr3.data.update(phase="open", session="s", ws=dict(a.WS_OWN), panes={a.PLAN: {"cwd": p}, a.RESEARCH: {"cwd": p}}, tasks={"T1": {"status": "verified"}}, builder="build-local", work_dir=None)
    mr3.save()
    def merged_win3(s, n):
        if n in (a.PLAN, a.RESEARCH, "build-local"): return {"custom_name": n, "cwd": p}
        return None
    a.window_named = merged_win3
    def merged_state3(s, n):
        if n == a.RESEARCH: return "working"
        if n == "build-local": return "idle"
        return "idle"
    a.agent_state = merged_state3
    merged_calls.clear()
    merged_captured[0] = "New session started\n"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_merged(mr3, [])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("merged does not reset working Lumo", rc == 0 and "not reset" in printed and len([t for t in merged_calls if t[0] == "send-text" and len(t) > 4 and t[4] == "build-local"]) >= 1 and not any(t[0] == "send-text" and len(t) > 4 and t[4] == a.RESEARCH for t in merged_calls), (printed, merged_calls))

    # Case 4
    mr4 = a.Run(p, "20260101-000013")
    mr4.data.update(phase="open", session="s", ws=dict(a.WS_OWN), panes={a.PLAN: {"cwd": p}, a.RESEARCH: {"cwd": p}}, tasks={"T1": {"status": "verified"}}, work_dir=None)
    mr4.save()
    def merged_win4(s, n):
        if n in (a.PLAN, a.RESEARCH, "build-local", "build-free", "build-billed"): return {"custom_name": n, "cwd": p}
        return None
    a.window_named = merged_win4
    a.agent_state = lambda s, n: "idle"
    merged_calls.clear()
    merged_captured[0] = "New session started\n"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_merged(mr4, [])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    texts = [c for c in merged_calls if c[0] == "send-text"]
    check("merged resets different builders with correct commands", rc == 0 and 
          any(len(t) > 5 and t[4] == "build-local" and t[5] == "/new" for t in texts) and
          any(len(t) > 5 and t[4] == "build-free" and t[5] == "/new" for t in texts) and
          any(len(t) > 5 and t[4] == "build-billed" and t[5] == "/clear" for t in texts), (texts, printed))

    # Case 5
    mr5 = a.Run(p, "20260101-000014")
    mr5.data.update(phase="open", session="s", ws=dict(a.WS_OWN), panes={a.PLAN: {"cwd": p}, a.RESEARCH: {"cwd": p}}, tasks={"T1": {"status": "verified"}}, work_dir=p, builder="build-local")
    mr5.save()
    def merged_win5(s, n):
        if n in (a.PLAN, a.RESEARCH, "build-local"): return {"custom_name": n, "cwd": p}
        return None
    a.window_named = merged_win5
    a.agent_state = lambda s, n: "idle"
    merged_calls.clear()
    merged_captured[0] = "New session started\n"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_merged(mr5, [])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("merged closes builders if work_dir exists before resets", rc == 0 and any(c[0] == "close-window" and "build-local" in str(c) for c in merged_calls), (merged_calls, printed))
    mr5r = a.Run(p, "20260101-000014")
    check("merged removes work_dir via finish", mr5r.data.get("work_dir") is None)

    # Case 6
    mr6 = a.Run(p, "20260101-000015")
    mr6.data.update(phase="open", session="s", ws=dict(a.WS_OWN), panes={a.PLAN: {"cwd": p}, a.RESEARCH: {"cwd": p}}, tasks={"T1": {"status": "verified"}}, builder="build-local", work_dir=None)
    mr6.save()
    def merged_win6(s, n):
        if n == a.PLAN: return {"custom_name": n, "cwd": p}
        if n == a.RESEARCH: return {"custom_name": n, "cwd": p}
        if n == "build-local": return {"custom_name": n, "cwd": "/no/such/dir/that/does/not/exist"}
        return None
    a.window_named = merged_win6
    a.agent_state = lambda s, n: "idle"
    merged_calls.clear()
    merged_captured[0] = "New session started\n"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_merged(mr6, [])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("merged warns when cwd gone but still resets", rc == 0 and "its directory" in printed and "is gone" in printed and any(t[0] == "send-text" and len(t) > 4 and t[4] == "build-local" for t in merged_calls), (printed, merged_calls))

    # Case 7
    mr7 = a.Run(p, "20260101-000016")
    mr7.data.update(phase="open", session="s", ws=dict(a.WS_OWN), panes={a.PLAN: {"cwd": p}, a.RESEARCH: {"cwd": p}}, tasks={"T1": {"status": "verified"}}, builder="build-local", work_dir=None)
    mr7.save()
    def merged_win7(s, n):
        if n in (a.PLAN, a.RESEARCH, "build-local"): return {"custom_name": n, "cwd": p}
        return None
    a.window_named = merged_win7
    a.agent_state = lambda s, n: "idle"
    merged_calls.clear()
    merged_captured[0] = "still working...\n"
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_merged(mr7, [])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    count_unconfirmed = printed.count("reset not confirmed")
    check("merged prints reset not confirmed once per pane", rc == 0 and count_unconfirmed == 2, (count_unconfirmed, printed))

    # Case 8
    hr2 = a.Run(p, "20260101-000017")
    hr2.data.update(phase="open", session="s", ws=dict(a.WS_OWN), panes={a.PLAN: {"cwd": p}}, work_dir=p, builder="build-local")
    hr2.save()
    calls_finish = []
    a.tuios = lambda *args, timeout=60: (calls_finish.append(args), (0, "", ""))[1]
    a.window_named = lambda s, n: {"custom_name": n, "cwd": p} if n == "build-local" else None
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_finish(hr2, [])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("finish output unchanged", rc == 0 and "finished. Changes are uncommitted in" in printed, printed)

    # Restore state for original tests
    for rid in ["20260101-000010", "20260101-000011", "20260101-000012", "20260101-000013", 
               "20260101-000014", "20260101-000015", "20260101-000016", "20260101-000017"]:
        try:
            tr = a.Run(p, rid)
            tr.data["phase"] = "done"
            tr.save()
        except Exception:
            pass

    a.tuios, a.time.sleep, a.window_named, a.agent_state = real_tuios_m, real_sleep_m, real_wn_m, real_as_m
    print("Lumo pane")
    lumo_dir = os.path.join(d, "pi-lumo")
    os.makedirs(lumo_dir, exist_ok=True)
    a.write_lumo_pi({"pi_lumo": lumo_dir}, ("http://127.0.0.1:3003/v1", "sekrit-key"))
    models = open(os.path.join(lumo_dir, "models.json")).read()
    check("the tamer key is in a 0600 file, not in models.json",
          os.stat(os.path.join(lumo_dir, "lumo.key")).st_mode & 0o777 == 0o600 and "sekrit-key" not in models
          and "!cat" in models)
    lsid = hr.data["panes"].setdefault(a.RESEARCH, {}).setdefault("session_id", "lumo-1")
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
            say("a2", "assistant", "Use X 2.0; see https://example.org\n"
                "SEARCH-CONFIRMATION: searched=yes; queries=x release notes; sources=1")
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
    check("the question goes to the research pane", asks and a.RESEARCH in asks[-1] and asks[-1][-1].endswith("which X?"), asks)
    say("u3", "user", "typed by you in the lumo pane")
    say("a3", "assistant", "Lumo answer three")
    a.tuios_json = lambda *args, **kw: {}
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_watch(hr, ["5"])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("watch reports a Lumo exchange it has not reported, and nothing older",
          rc == 0 and "typed by you" in printed and "Lumo answer three" in printed and "X 2.0" not in printed, printed)

    print("Claude pane")
    ccfg = {"claude_settings": os.path.join(d, "s.json"), "claude_mcp": "/m.json",
            "claude_backbone": os.path.join(d, "b.json")}
    a.wj(ccfg["claude_settings"], {"hooks": {"x": 1}})
    body = a.claude_pane_body(hr, ccfg, "add subtract", True)
    check("the backbone runs with advisor off and knows its run",
          "export CLAUDE_ADVISOR=off" in body and f"AIDEV_TUIOS_RUN={hr.id}" in body)
    check("the Claude panes load only the tuios MCP", "--strict-mcp-config" in body)
    bs = json.load(open(ccfg["claude_backbone"]))
    check("its settings keep tuios's hooks and allow the helpers",
          bs["hooks"].get("x") == 1
          and any("plan_mcp_guard" in h.get("command", "")
                  for e in bs["hooks"].get("PreToolUse", []) for h in e.get("hooks", []))
          and any("aidev_tuios.py" in x for x in bs["permissions"]["allow"]))
    check("it runs in the default output style, not Advisor", bs.get("outputStyle") == "default")
    sysp = open(os.path.join(hr.dir, "bin", "plan.system.md")).read()
    check("its prompt names the helpers and has no placeholder left", "ask-lumo" in sysp and "@@" not in sysp)
    check("the builder holds less than Claude, so it cannot type into Claude's pane",
          set(a.GRANTS["build"].split(",")) < set(a.GRANTS[a.PLAN].split(",")))
    check("claude_body includes --strict-mcp-config flag", "--strict-mcp-config" in body)
    a.window_named = lambda s, n: {"custom_name": n}
    hr.data.update(work_dir=p, builder="build-local")
    check("finish closes the builder pane and keeps the run open for the next piece of work",
          a.cmd_finish(hr, []) == 0 and hr.data.get("phase") != "done" and not hr.data.get("work_dir")
          and hr.data["finished"][-1]["work_dir"] == p and any(c[:2] == ("close-window", "build-local") for c in calls))
    rr = a.Run(p, "20260101-000006")
    rr.data.update(session="dev-r", phase="done", panes={a.PLAN: {"script": script, "cwd": p}})
    rr.save()
    check("a session's run is found by its plan pane",
          a.session_run(p, "dev-r") is not None and a.session_run(p, "dev-r").id == rr.id and not a.session_run(p, "x"))
    a.tuios, a.window_named, a.agent_state, a.tuios_json = real_t
    hr.data["phase"] = "done"
    hr.save()

    print("script forms")
    rdir = os.path.join(d, "ai-home", "rfcs")
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, "2026-01-01-x.md"), "w") as fh:
        fh.write("# x\n")
    real_ai_home, a.AI_HOME = a.AI_HOME, os.path.join(d, "ai-home")
    task, err = a.rfc_task("2026-01-01-x", ["and", "y"])
    check("--rfc finds a name in ~/.ai/rfcs and names the file for Claude",
          not err and os.path.join(rdir, "2026-01-01-x.md") in task and task.endswith("Also: and y"), (task, err))
    check("--rfc refuses an unknown name", a.rfc_task("nope", [])[1])
    a.AI_HOME = real_ai_home
    ep = project()
    before = a.tree_state(ep)
    check("an edit that changes nothing is not done", a.check_edit(ep, before, "") == "it changed nothing")
    with open(os.path.join(ep, "calc.py"), "a") as fh:
        fh.write("\n\ndef sub(a, b):\n    return a - b\n")
    check("a changed tree with a passing check is done", a.check_edit(ep, before, "python3 -c 'import calc'") == "")
    check("a failing AIDEV_TEST_CMD is reported", "exits 3" in a.check_edit(ep, before, "exit 3"))
    subprocess.run(["git", "checkout", "-q", "calc.py"], cwd=ep, check=False)

    attempts = []

    def fake_headless(run, kind, task_text, limit):
        attempts.append(kind)
        if kind == "free":
            with open(os.path.join(run.data["work_dir"], "calc.py"), "a") as fh:
                fh.write("\n\ndef sub(a, b):\n    return a - b\n")
        return f"{kind} did its turn", ""

    saved_env = {k: os.environ.get(k) for k in ("TUIOS_ENV", "AIDEV_TEST_CMD", "AIDEV_TUIOS_BUILDER")}
    os.environ.pop("TUIOS_ENV", None)
    os.environ["AIDEV_TEST_CMD"] = "python3 -c 'import calc; calc.sub'"
    real_headless, real_coder = a.edit_headless, a.CODER_FILE
    a.edit_headless, a.CODER_FILE = fake_headless, os.path.join(ep, "calc.py")  # any existing file: "the 30B is here"
    cwd0 = os.getcwd()
    os.chdir(ep)
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_edit(["add sub(a, b) to calc.py", "calc.py"])
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    check("-p tries the 30B, then the Zen builder when the check still fails",
          rc == 0 and attempts == ["local", "free"] and "aidev -p: done" in printed, (rc, attempts, printed[-400:]))
    check("-p never becomes the project's run", a.Run(ep).id.startswith("edit-") is False)
    os.environ["AIDEV_TUIOS_BUILDER"] = "1"
    check("-p is refused inside a builder pane", a.cmd_edit(["x"]) == 2)
    os.chdir(cwd0)
    a.edit_headless, a.CODER_FILE = real_headless, real_coder
    for k, v in saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    hp = project()
    hdir = os.path.join(d, "handoff")
    os.makedirs(hdir, exist_ok=True)
    a.wj(os.path.join(hdir, "prd.json"), {"name": "x", "title": "Add x", "description": "d.", "userStories": [
        {"id": "T1", "title": "t", "description": "d", "acceptanceCriteria": ["c"], "priority": 1, "passes": False,
         "dependsOn": []}]})
    a.wj(os.path.join(hdir, "verify.json"), {"T1": ["true ; false"]})
    os.chdir(hp)
    real_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = a.cmd_handoff([hdir])
        out = json.loads(sys.stdout.getvalue().strip().splitlines()[-1])
        rc2 = a.cmd_handoff([os.path.join(d, "no-such-dir")])
        out2 = json.loads(sys.stdout.getvalue().strip().splitlines()[-1])
    finally:
        sys.stdout = real_stdout
        os.chdir(cwd0)
    check("--handoff refuses a plan that breaks aistack's rules, as JSON problems",
          rc == 1 and out.get("problems") and not out.get("started"), out)
    check("--handoff without the plan files says so", rc2 == 1 and "prd.json" in out2.get("problem", ""), out2)

    er = a.Run(p, "edit-20260101-000000")
    er.data.update(phase="edit", work_dir=p, reply_to="abcd-pane")
    body = a.build_body(er, {"pi_build": os.path.join(d, "pi-b"), "opencode_dir": d,
                             "claude_backbone": os.path.join(d, "b.json"), "claude_settings": ccfg["claude_settings"],
                             "claude_mcp": "/m.json"}, "billed", "edit-claude-x")
    sp = open(os.path.join(er.dir, "bin", "edit-claude-x.system.md")).read()
    check("an edit's builder replies to the caller's pane, and cannot run aidev itself",
          "-w abcd-pane" in sp and "AIDEV_TUIOS_BUILDER=1" in body, sp[:300])

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
