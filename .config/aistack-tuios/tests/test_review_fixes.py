"""Test the review fixes: tripped tasks escalate at once, a verified task trips only on a turn after done, and wait-task reports every guard trip."""

import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []
BUILDER = "build-local-tier-2"


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def fake_run(tasks, tmp):
    return types.SimpleNamespace(
        session="s",
        dir=tmp,
        data={"tasks": tasks, "work_dir": "/wd", "builder": BUILDER},
        event=lambda *_args, **_kw: None,
        save=lambda: None,
    )


def stubbed(names, fn):
    """Run fn with the module attributes in `names` replaced by the values in the dict, then restore them."""
    real = {name: getattr(a, name) for name in names}
    for name, value in names.items():
        setattr(a, name, value)
    try:
        return fn()
    finally:
        for name, value in real.items():
            setattr(a, name, value)


def test_escalate(tmp):
    calls = []
    erun = fake_run({}, tmp)

    def esc(task):
        erun.data.update(builder="build-local", tasks={"T1": task})
        calls.clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = a.cmd_escalate(erun, ["T1"])
        return code, buf.getvalue()

    stubs = {
        "zen_status": lambda r, refresh=False: {"state": "available", "detail": ""},
        "cmd_builder": lambda r, argv: (calls.append(argv), 0)[1],
        "tuios": lambda *args, **kw: (0, "", ""),
    }
    code, out = stubbed(
        stubs,
        lambda: esc(
            {
                "status": "failed",
                "attempts": 1,
                "by": {"build-local": 1},
                "tripped": "loop",
            }
        ),
    )
    check(
        "escalate accepts a tripped task after one attempt",
        code == 0 and calls == [["tier-3"]],
        (code, calls, out),
    )
    code, out = stubbed(
        stubs,
        lambda: esc(
            {"status": "failed", "attempts": 1, "by": {"build-local": 1}}
        ),
    )
    check(
        "escalate refuses an untripped task after one attempt",
        code == 1 and not calls,
        (code, calls, out),
    )


def test_poll(tmp):
    def poll(task_guard, calls):
        t = {"status": "verified", "attempts": 1, "notes": [], "guard": task_guard}
        run = fake_run({"T1": t}, tmp)
        stubs = {
            "agent_state": lambda *_args, **_kw: "idle",
            "agent_info": lambda *_args, **_kw: {},
            "tool_log_path": lambda *_args, **_kw: "/none",
            "git_out": lambda *_args, **_kw: "",
            "pane_text": lambda *_args, **_kw: "",
            "tuios": lambda *_args, **_kw: (0, "", ""),
            "wait_rest": lambda *_args, **_kw: True,
            "tier_of": lambda *_args, **_kw: "tier-2",
            "reset_pane": lambda *_args, **_kw: resets.append(1),
        }
        real_read = a.aidev_guard.read_tool_log
        a.aidev_guard.read_tool_log = lambda *_args, **_kw: (calls, 5)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                res = stubbed(stubs, lambda: a.guard_poll(run, BUILDER, "T1"))
        finally:
            a.aidev_guard.read_tool_log = real_read
        return res, t

    now = time.time()
    expired = {
        "start": now - a.aidev_guard.TASK_WALL_S - 100,
        "last_progress": now,
        "turns": 0,
        "recent": [],
        "diff": None,
        "done_at": now - 10,
        "calls_known": True,
    }
    resets = []
    res, t = poll(dict(expired), [])
    check(
        "guard_poll ignores a wall clock trip on a verified task",
        res is False and t["status"] == "verified" and not resets,
        (res, t, resets),
    )
    check("the guard state is stored", t["guard"].get("offset") == 5, t["guard"])
    call = {"tool": "bash", "args": "ls", "out": "x"}
    res, t = poll(dict(expired), [call])
    check(
        "a new call after done resets and the task stays verified",
        res is True and t["status"] == "verified" and len(resets) == 1,
        (res, t, resets),
    )


def test_overflow(tmp):
    def trip(t, reason):
        run = fake_run({"T1": t}, tmp)
        stubs = {
            "tuios": lambda *_args, **_kw: (0, "", ""),
            "wait_rest": lambda *_args, **_kw: True,
            "tier_of": lambda *_args, **_kw: "tier-2",
            "reset_pane": lambda *_args, **_kw: True,
            "git_out": lambda *_args, **_kw: "diff",
        }
        with contextlib.redirect_stdout(io.StringIO()):
            stubbed(stubs, lambda: a.guard_trip(run, BUILDER, "T1", reason))

    t = {"status": "sent", "attempts": 1, "notes": []}
    trip(t, "context overflow")
    check(
        "a first overflow sets trip_reason and not tripped",
        t.get("trip_reason") == "context overflow" and not t.get("tripped"),
        t,
    )
    trip(t, "context overflow")
    check(
        "the second overflow sets tripped",
        t.get("tripped") == "context overflow",
        t,
    )


def test_wait(tmp):
    t = {
        "status": "failed",
        "thread": "th",
        "builder": BUILDER,
        "trip_reason": "context overflow",
    }
    run = fake_run({"T1": t}, tmp)
    verified = []
    stubs = {
        "wait_reply": lambda *_args, **_kw: ("looped", ""),
        "check_task": lambda *_args, **_kw: verified.append(1) or 0,
    }
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = stubbed(stubs, lambda: a.cmd_wait_task(run, ["T1", "5"]))
    check(
        "wait-task prints TRIPPED for a first overflow and exits 1",
        code == 1
        and "TRIPPED (context overflow)" in buf.getvalue()
        and not verified
        and "trip_reason" not in t,
        (code, buf.getvalue(), verified),
    )


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_escalate(tmp)
        test_poll(tmp)
        test_overflow(tmp)
        test_wait(tmp)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
