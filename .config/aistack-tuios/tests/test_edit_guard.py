"""Tests for the builder guard inside an `aidev -p` edit run (aidev_tuios.py edit_in_pane / cmd_edit): a looping builder
is stopped and the next tier is tried, a context overflow retries the same tier once and then escalates, a normal
reply does not trip. No tuios daemon, no model, no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_edit_guard.py
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

os.environ["AISTACK_ZEN_KEY"] = "1"
os.environ["AIDEV_REMOTE_BUILDER"] = "off"
os.environ["AIDEV_SEMI_LOCAL"] = "off"
os.environ["AIDEV_GUARD"] = "on"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ.setdefault("AISTACK_DIR", os.path.realpath(os.path.join(ROOT, "..", "aistack")))
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


def make_repo():
    p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-edit-guard-"))
    with open(os.path.join(p, "calc.py"), "w") as fh:
        fh.write("def add(a, b):\n    return a + b\n")
    subprocess.run(["git", "init", "-q"], cwd=p, check=False)
    subprocess.run(["git", "add", "."], cwd=p, check=False)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init"], cwd=p,
                   check=False)
    return p


def new_run(a, repo, rid):
    run = a.Run(repo, rid)
    run.data.update(phase="edit", work_dir=repo, session="s", reply_to="p",
                    tasks={"edit": {"status": "pending", "attempts": 0, "notes": [], "overflows": 0}})
    return run


def quiet(fn, *args):
    """fn(*args) with stdout and stderr swallowed; (result, stdout text)."""
    real_out, real_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        res = fn(*args)
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout, sys.stderr = real_out, real_err
    return res, printed


def main():
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ.pop("AIDEV_TUIOS_BUILDER", None)
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))
    g = a.aidev_guard
    repo = make_repo()

    names = ("tuios", "agent_state", "agent_info", "pane_text", "wait_rest", "reset_pane", "mail_task", "ai_workspace",
             "start_builder", "window_named", "reply_line", "thread_replies", "tier_online", "zen_status", "check_edit")
    real = {n: getattr(a, n) for n in names}
    saved_env = {k: os.environ.get(k) for k in ("TUIOS_ENV", "TUIOS_SESSION", "TUIOS_PANE_ID", "AIDEV_TEST_CMD",
                                                "AIDEV_TUIOS_BUILDER", "AIDEV_TUIOS_EDIT_TIMEOUT_S")}
    state = {"builder": "", "run": None, "loop": False, "overflow_for": (), "starts": [], "reply": False}
    overflow_text = "error: the request exceeds the available context size (65536 tokens)"

    def fake_tuios(*args, **kw):
        if state["loop"] and args and args[0] == "wait-for" and state["run"] and state["builder"]:
            path = a.tool_log_path(state["run"], state["builder"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a") as fh:
                fh.writelines(json.dumps({"tool": "read", "args": "calc.py", "out": ""}) + "\n" for _ in range(g.LOOP_REPEAT + 1))
        return 0, "", ""

    def fake_start(run, kind, name, ws, cwd):
        state["builder"] = name
        state["starts"].append(kind)
        return True, "ok"

    def fake_pane_text(session, name, n=12):
        return overflow_text if any(name.endswith(k) for k in state["overflow_for"]) else ""

    def fake_replies(session, me, thread):
        return [(0, 0, "done")] if state["reply"] else []

    try:
        a.tuios = fake_tuios
        a.agent_state = lambda session, name: "working"
        a.agent_info = lambda session, name: {}
        a.pane_text = fake_pane_text
        a.wait_rest = lambda session, name, limit: True
        a.reset_pane = lambda run, name, cmd: True
        a.mail_task = lambda run, builder, subject, mail_text, prompt: "m1"
        a.ai_workspace = lambda session: 1
        a.start_builder = fake_start
        a.window_named = lambda session, name: {"window_id": "w1"}
        a.reply_line = lambda run, mid: "x"
        a.thread_replies = fake_replies
        a.zen_status = lambda r, refresh=False: {"state": "off", "model": "", "detail": "off", "models": []}
        os.environ["TUIOS_PANE_ID"] = "p"
        os.environ["AIDEV_TUIOS_EDIT_TIMEOUT_S"] = "20"

        print("looping builder")
        run = new_run(a, repo, "edit-20260101-000001")
        state.update(run=run, loop=True, overflow_for=(), starts=[], reply=False)
        task_path = a.write_text(os.path.join(run.dir, "tasks", "edit.md"), "do it\n")
        (res, _out) = quiet(a.edit_in_pane, run, "tier-2", task_path, 30)
        reply, err = res
        t = run.data["tasks"]["edit"]
        check("the guard stops the loop", err.startswith("guard stopped"), (reply, err))
        check("the task is tripped as loop", t.get("tripped") == "loop" and t.get("status") == "failed", t)
        check("a note says the builder was reset", any("stopped by the guard (loop)" in n for n in t["notes"]),
              t["notes"])
        events = ""
        ev_path = os.path.join(run.dir, "events.jsonl")
        if os.path.exists(ev_path):
            with open(ev_path) as fh:
                events = fh.read()
        check("a guard_trip event is recorded", "guard_trip" in events or "stopped by the guard" in "".join(t["notes"]),
              events[:200])

        print("looping builder, next tier")
        state.update(run=None, loop=True, overflow_for=(), starts=[], reply=False)
        # the loop stub needs the run of cmd_edit; find it through the builder name's run id on each start
        orig_start = a.start_builder

        def start_and_bind(run_, kind, name, ws, cwd):
            state["run"] = run_
            return orig_start(run_, kind, name, ws, cwd)

        a.start_builder = start_and_bind
        os.environ.update(TUIOS_ENV="1", TUIOS_SESSION="s", TUIOS_PANE_ID="p")
        os.environ.pop("AIDEV_TEST_CMD", None)
        a.tier_online = lambda tid, run=None: tid in ("tier-2", "tier-1")
        a.check_edit = lambda cwd, before, test_cmd: "it changed nothing"
        cwd0 = os.getcwd()
        os.chdir(repo)
        try:
            (rc, _out) = quiet(a.cmd_edit, ["-p", "change it"])
        finally:
            os.chdir(cwd0)
        check("a looping tier-2 is stopped, then tier-1 is tried", state["starts"][:2] == ["tier-2", "tier-1"],
              state["starts"])
        check("a loop escalates at once (no same-tier retry)", state["starts"].count("tier-2") == 1, state["starts"])
        check("cmd_edit fails when nothing changed", rc == 1, rc)
        a.start_builder = fake_start

        print("context overflow")
        run = new_run(a, repo, "edit-20260101-000002")
        state.update(run=run, loop=False, overflow_for=("tier-2",), starts=[], reply=False)
        task_path = a.write_text(os.path.join(run.dir, "tasks", "edit.md"), "do it\n")
        (res, _out) = quiet(a.edit_in_pane, run, "tier-2", task_path, 30)
        reply, err = res
        t = run.data["tasks"]["edit"]
        check("the first overflow stops the builder", err.startswith("guard stopped"), (reply, err))
        check("the first overflow does not set tripped", "tripped" not in t, t)
        check("the first overflow adds a handoff note", len(t["notes"]) == 1 and t.get("overflows") == 1, t)

        print("context overflow through cmd_edit")
        state.update(run=None, loop=False, overflow_for=("tier-2",), starts=[], reply=False)
        cwd0 = os.getcwd()
        os.chdir(repo)
        try:
            (rc, _out) = quiet(a.cmd_edit, ["-p", "change it again"])
        finally:
            os.chdir(cwd0)
        check("tier-2 runs twice for overflow, then tier-1 once", state["starts"] == ["tier-2", "tier-2", "tier-1"],
              state["starts"])

        print("normal reply")
        a.tuios = fake_tuios
        run = new_run(a, repo, "edit-20260101-000003")
        state.update(run=run, loop=False, overflow_for=(), starts=[], reply=True)
        task_path = a.write_text(os.path.join(run.dir, "tasks", "edit.md"), "do it\n")
        (res, _out) = quiet(a.edit_in_pane, run, "tier-2", task_path, 30)
        reply, err = res
        t = run.data["tasks"]["edit"]
        check("a reply returns without an error", reply == "done" and not err, (reply, err))
        check("the guard does not trip", "tripped" not in t and t.get("status") == "pending", t)
    finally:
        for n, v in real.items():
            setattr(a, n, v)
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
    return 1 if FAILS else 0


sys.exit(main())
