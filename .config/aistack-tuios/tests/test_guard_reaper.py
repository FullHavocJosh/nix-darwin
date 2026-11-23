"""Test aidev_guard.py: reap_due function and RestTracker class."""

import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_guard", os.path.join(HERE, "..", "aidev_guard.py")
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


class StubClock:
    """A stub clock for tests."""

    def __init__(self, now=None):
        self._now = now if now is not None else time.time()

    def time(self):
        return self._now

    def advance(self, s):
        self._now += s


def main():
    # Test reap_due function
    clock = StubClock(now=0)

    # Test: working state never due
    check(
        "reap_due: working state never due",
        a.reap_due("working", 100, 220, False, False) == False,
    )

    # Test: idle 119 s not due
    check(
        "reap_due: idle 119 s not due",
        a.reap_due("idle", 119, 220, False, False) == False,
    )

    # Test: idle 120 s due (now - since == 120)
    check(
        "reap_due: idle 120 s due",
        a.reap_due("idle", 100, 220, False, False) == True,
    )

    # Test: done 29 s not due
    check(
        "reap_due: done 29 s not due",
        a.reap_due("done", 29, 58, False, False) == False,
    )

    # Test: done 30 s not due (plan_done=False, limit is 120 s)
    check(
        "reap_due: done 30 s not due (plan_done=False)",
        a.reap_due("done", 30, 58, False, False) == False,
    )

    # Test: done 120 s due (plan_done=False)
    check(
        "reap_due: done 120 s due (plan_done=False)",
        a.reap_due("done", 0, 120, False, False) == True,
    )

    # Test: plan_done 29 s not due
    check(
        "reap_due: plan_done 29 s not due",
        a.reap_due("idle", 29, 58, False, True) == False,
    )

    # Test: plan_done 30 s due
    check(
        "reap_due: plan_done 30 s due",
        a.reap_due("idle", 30, 60, False, True) == True,
    )

    # Test: task_queued blocks
    check(
        "reap_due: task_queued blocks",
        a.reap_due("idle", 120, 220, True, False) == False,
    )

    # Test: task_queued blocks with plan_done
    check(
        "reap_due: task_queued blocks with plan_done",
        a.reap_due("idle", 120, 220, True, True) == False,
    )

    # Test: state not in ('idle', 'done', 'none') returns False
    check(
        "reap_due: state 'working' returns False",
        a.reap_due("working", 120, 220, False, False) == False,
    )

    check(
        "reap_due: state 'pending' returns False",
        a.reap_due("pending", 120, 220, False, False) == False,
    )

    check(
        "reap_due: state 'running' returns False",
        a.reap_due("running", 120, 220, False, False) == False,
    )

    # Test: since is None returns False
    check(
        "reap_due: since is None returns False",
        a.reap_due("idle", None, 220, False, False) == False,
    )

    # Test RestTracker
    tracker = a.RestTracker(clock=StubClock(now=0).time)

    # Test: working state deletes entry and returns None
    check(
        "RestTracker.update: working state deletes entry",
        tracker.update("pane1", "working") is None,
    )
    check(
        "RestTracker.update: working state keeps None",
        tracker._resting.get("pane1") is None,
    )

    # Test: idle keeps first since (stub clock returns 0)
    clock = StubClock(now=0)
    tracker = a.RestTracker(clock=clock.time)
    check(
        "RestTracker.update: idle keeps first since",
        tracker.update("pane1", "idle") is not None,
    )
    check(
        "RestTracker.update: idle since is 0",
        tracker._resting["pane1"] == 0,
    )

    # Test: new idle resets since
    clock = StubClock(now=100)
    tracker = a.RestTracker(clock=clock.time)
    check(
        "RestTracker.update: new idle resets since",
        tracker.update("pane1", "idle") is not None,
    )
    check(
        "RestTracker.update: new idle since is 100",
        tracker._resting["pane1"] == 100,
    )

    # Test: done keeps since
    clock = StubClock(now=200)
    tracker = a.RestTracker(clock=clock.time)
    check(
        "RestTracker.update: done keeps since",
        tracker.update("pane1", "done") is not None,
    )

    # Test: none keeps since
    clock = StubClock(now=300)
    tracker = a.RestTracker(clock=clock.time)
    check(
        "RestTracker.update: none keeps since",
        tracker.update("pane1", "none") is not None,
    )

    # Test: forget clears
    clock = StubClock(now=0)
    tracker = a.RestTracker(clock=clock.time)
    tracker.update("pane1", "idle")
    check(
        "RestTracker.forget: clears entry",
        tracker.forget("pane1") is None,
    )
    check(
        "RestTracker.forget: entry deleted",
        "pane1" not in tracker._resting,
    )

    # Test: multiple panes
    clock = StubClock(now=0)
    tracker = a.RestTracker(clock=clock.time)
    tracker.update("pane1", "idle")
    tracker.update("pane2", "idle")
    check(
        "RestTracker.update: multiple panes tracked",
        "pane1" in tracker._resting and "pane2" in tracker._resting,
    )
    tracker.forget("pane1")
    check(
        "RestTracker.forget: one pane cleared",
        "pane1" not in tracker._resting and "pane2" in tracker._resting,
    )

    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
