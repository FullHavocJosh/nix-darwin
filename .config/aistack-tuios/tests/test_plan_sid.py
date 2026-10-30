"""Test cmd_plan_sid: store the plan pane's new session id after /clear, time out otherwise."""

import importlib.util
import os
import sys
import time
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


UUID = "12345678-90ab-cdef-1234-567890abcdef"

seq = iter(["old", "", UUID])
a.agent_session_id = lambda session, name: next(seq)
a.time = types.SimpleNamespace(sleep=lambda s: None, time=time.time)
run = types.SimpleNamespace(session="s", data={"panes": {}}, save=lambda: None)
check("new uuid returns 0", a.cmd_plan_sid(run, ["old"]) == 0)
check("uuid stored", run.data["panes"].get(a.PLAN, {}).get("session_id") == UUID)

clock = {"t": 0}


def jump():
    clock["t"] += 400
    return clock["t"]


a.agent_session_id = lambda session, name: "old"
a.time = types.SimpleNamespace(sleep=lambda s: None, time=jump)
run2 = types.SimpleNamespace(session="s", data={"panes": {}}, save=lambda: None)
check("timeout returns 1", a.cmd_plan_sid(run2, ["old"]) == 1)
check("nothing stored on timeout", "session_id" not in run2.data["panes"].get(a.PLAN, {}))

check("plan-sid registered", "plan-sid" in a.HELPERS)

sys.exit(1 if FAILS else 0)
