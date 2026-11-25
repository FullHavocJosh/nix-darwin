"""Test that a builder reply starting with 'blocked' is recorded as blocked, not as a failed attempt."""

import contextlib
import importlib.util
import inspect
import io
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


got = a.blocked_reply("blocked: need a/b.txt: why")
check("need reply parsed", got == ("need", "a/b.txt: why"), repr(got))
got = a.blocked_reply("  Blocked: the hook refuses edits")
check("other reply parsed", got == ("other", "the hook refuses edits"), repr(got))
got = a.blocked_reply("done: ok")
check("done reply is not blocked", got is None, repr(got))

run = types.SimpleNamespace(
    data={
        "tasks": {
            "T1": {"status": "pending", "attempts": 2, "notes": [], "by": {"b": 2}}
        }
    },
    event=lambda *x, **k: None,
    save=lambda: None,
)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = a.blocked_result(run, "T1", "b", "blocked: need a/b.txt: why")
out = buf.getvalue()
t = run.data["tasks"]["T1"]
check("blocked_result returns 4", rc == 4, repr(rc))
check("output holds NEEDS FILE", "NEEDS FILE" in out, out)
check("output holds the path", "a/b.txt" in out, out)
check("task status is blocked", t["status"] == "blocked", t["status"])
check("attempt does not count", t["by"]["b"] == 1, repr(t["by"]))
check("one note added", len(t["notes"]) == 1, repr(t["notes"]))

src = inspect.getsource(a.cmd_wait_task)
i, j = src.find("blocked_result("), src.find("replied (data")
check("blocked_result runs before the checks", 0 <= i < j, f"{i} {j}")

sys.exit(1 if FAILS else 0)
