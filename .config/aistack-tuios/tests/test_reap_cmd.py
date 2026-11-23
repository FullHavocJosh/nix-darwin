"""Tests for reap command and reap_pass function. Tests the check() style from test_loop_stop.py, no unittest or mock."""

import importlib.util
import os
import sys
import types

os.environ["AIDEV_TUIOS_NO_REAPER"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond):
    print("PASS" if cond else "FAIL", name)
    (not cond) and FAILS.append(name)


def case(state, tasks, now, since=0):
    """Returns (open_count, closed_names)."""
    closed = []
    a.tuios = lambda *args, **kw: (
        (closed.append(args[1]) if args and args[0] == "close-window" else None)
        or (0, "", "")
    )
    a.window_named = lambda s, n: {"x": 1} if n == a.BUILDERS["tier-1"] else None
    a.agent_state = lambda s, n: state
    a.guard_poll = lambda *x, **k: False
    a.rj = lambda *x, **k: None
    tracker = a.aidev_guard.RestTracker(clock=lambda: since)
    run = types.SimpleNamespace(
        session="s",
        data={"tasks": tasks, "builder": a.BUILDERS["tier-1"], "work_dir": "/tmp/wd"},
        event=lambda *x, **k: None,
        save=lambda: None,
        dir="/tmp",
        path="/tmp/none",
    )
    tracker.update(a.BUILDERS["tier-1"], state)
    n = a.reap_pass(run, tracker, now=now)
    return n, closed


# Test cases
# idle builder with no task closed after 120 s, not at 119
n, closed = case("idle", {}, now=120)
check(
    "idle builder closed at 120",
    n == 0 and len(closed) == 1 and closed[0] == a.BUILDERS["tier-1"],
)

n, closed = case("idle", {}, now=119)
check("idle builder not closed at 119", n == 1 and len(closed) == 0)

# working builder never closed
n, closed = case("working", {}, now=500)
check("working builder never closed", n == 1 and len(closed) == 0)

# builder with a 'sent' task never closed
n, closed = case(
    "idle", {"t1": {"status": "sent", "builder": a.BUILDERS["tier-1"]}}, now=500
)
check("builder with sent task never closed", n == 1 and len(closed) == 0)

# all tasks verified closes at 30 s
n, closed = case(
    "idle", {"t1": {"status": "verified", "builder": a.BUILDERS["tier-1"]}}, now=30
)
check(
    "all tasks verified closes at 30",
    n == 0 and len(closed) == 1 and closed[0] == a.BUILDERS["tier-1"],
)

n, closed = case(
    "idle", {"t1": {"status": "verified", "builder": a.BUILDERS["tier-1"]}}, now=29
)
check("all tasks verified not closed at 29", n == 1 and len(closed) == 0)

# reap_pass returns 1 when not closed
n, closed = case("idle", {}, now=119)
check("reap_pass returns open count", n == 1)

# reap --once returns 0
run = types.SimpleNamespace(
    session="s",
    data={"tasks": {}},
    event=lambda *x, **k: None,
    save=lambda: None,
    dir="/tmp",
    path="/tmp/none",
)
result = a.cmd_reap(run, ["--once"])
check("cmd_reap --once returns 0", result == 0)

sys.exit(1 if FAILS else 0)
