"""Test aidev_guard.py: constants, TaskGuard trip logic and round-trip."""

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
        self._now = now or time.time()

    def time(self):
        return self._now

    def advance(self, s):
        self._now += s


def main():
    # Test constants are set to defaults
    check(
        "IDLE_REAP_S default",
        a.IDLE_REAP_S == 120,
        f"{a.IDLE_REAP_S}",
    )
    check(
        "PLAN_DONE_REAP_S default",
        a.PLAN_DONE_REAP_S == 30,
        f"{a.PLAN_DONE_REAP_S}",
    )
    check(
        "TASK_WALL_S default",
        a.TASK_WALL_S == 900,
        f"{a.TASK_WALL_S}",
    )
    check(
        "TASK_TURNS default",
        a.TASK_TURNS == 40,
        f"{a.TASK_TURNS}",
    )
    check(
        "LOOP_REPEAT default",
        a.LOOP_REPEAT == 3,
        f"{a.LOOP_REPEAT}",
    )
    check(
        "HASH_REPEAT default",
        a.HASH_REPEAT == 2,
        f"{a.HASH_REPEAT}",
    )
    check(
        "NO_PROGRESS_S default",
        a.NO_PROGRESS_S == 300,
        f"{a.NO_PROGRESS_S}",
    )

    # Test env override - need to reimport with env var set
    saved_wall = os.environ.pop("AIDEV_GUARD_TASK_WALL_S", None)
    try:
        os.environ["AIDEV_GUARD_TASK_WALL_S"] = "1800"
        spec2 = importlib.util.spec_from_file_location(
            "aidev_guard", os.path.join(HERE, "..", "aidev_guard.py")
        )
        a_env = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(a_env)
        check(
            "TASK_WALL_S env override",
            a_env.TASK_WALL_S == 1800,
            f"{a_env.TASK_WALL_S}",
        )
    finally:
        if saved_wall is None:
            os.environ.pop("AIDEV_GUARD_TASK_WALL_S", None)
        else:
            os.environ["AIDEV_GUARD_TASK_WALL_S"] = saved_wall

    # Test TaskGuard with stub clock
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)

    check(
        "no trip under limits",
        guard.observe([], None) is None,
    )

    # Test wall clock
    clock.advance(a.TASK_WALL_S + 1)
    check(
        "wall clock trips",
        guard.observe([], None) == "wall clock",
    )

    # Test turns
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    for i in range(a.TASK_TURNS):
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': ''}], None)
    check(
        "turns trips on 40th call",
        guard.turns == 40,
        f"{guard.turns}",
    )
    clock.advance(1)
    check(
        "turns trips after 40 calls",
        guard.observe([], None) == "turns",
    )

    # Test loop (3 identical calls)
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    for i in range(2):
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out'}], None)
    check(
        "3 identical trip on loop",
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out'}], None) == "loop",
    )
    clock.advance(1)
    check(
        "4 identical still trips on loop",
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out'}], None) == "loop",
    )

    # Test same output twice (non-empty out equal to previous call's out)
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    guard.observe([{'tool': 'bash', 'args': 'echo hi', 'out': 'hi'}], None)
    check(
        "same non-empty output twice trips",
        guard.observe([{'tool': 'bash', 'args': 'echo hi', 'out': 'hi'}], None) == "same output",
    )

    # Test empty out does not trip (but loop check will trigger after 3 calls)
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    check(
        "empty out does not trip on first call",
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': ''}], None) is None,
    )
    check(
        "empty out does not trip on second call",
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': ''}], None) is None,
    )
    check(
        "empty out trips on loop on third call",
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': ''}], None) == "loop",
    )

    # Test no progress after 300s
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    guard.observe([{'tool': 'bash', 'args': 'ls', 'out': ''}], None)
    clock.advance(a.NO_PROGRESS_S + 1)
    check(
        "no progress after 300 s",
        guard.observe([], None) == "no progress",
    )

    # Test diff change resets progress
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out1'}], None)
    clock.advance(a.NO_PROGRESS_S + 1)
    check(
        "before diff change, no progress trips",
        guard.observe([], None) == "no progress",
    )
    guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out2'}], "new_diff")
    check(
        "after diff change, no progress does not trip immediately",
        guard.observe([], None) is None,
    )

    # Test new call resets progress
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out1'}], None)
    clock.advance(a.NO_PROGRESS_S + 1)
    check(
        "before new call, no progress trips",
        guard.observe([], None) == "no progress",
    )
    guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out2'}], None)
    check(
        "after new call, no progress does not trip immediately",
        guard.observe([], None) is None,
    )

    # Test done then call
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    guard.mark_done()
    check(
        "done_at is set after mark_done",
        guard.done_at is not None,
    )
    guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out'}], None)
    clock.advance(1)
    check(
        "done then call trips turn after done",
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out'}], None) == "turn after done",
    )

    # Test done with no call does not trip
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    guard.mark_done()
    check(
        "done with no call does not trip",
        guard.observe([], None) is None,
    )

    # Test calls_known False trips only on wall clock
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=False)
    clock.advance(a.TASK_WALL_S + 1)
    check(
        "calls_known=False trips only on wall clock",
        guard.observe([], None) == "wall clock",
    )
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=False)
    for i in range(a.LOOP_REPEAT):
        guard.observe([{'tool': 'bash', 'args': 'ls', 'out': ''}], None)
    clock.advance(1)
    check(
        "calls_known=False trips on loop after LOOP_REPEAT identical calls",
        guard.observe([], None) == "loop",
    )

    # Test to_dict/from_dict round trip
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    guard.observe([{'tool': 'bash', 'args': 'ls', 'out': 'out'}], None)
    guard.mark_done()
    d = guard.to_dict()
    guard2 = a.TaskGuard.from_dict(d, clock=clock.time, calls_known=True)
    check(
        "to_dict/from_dict round trip",
        guard2.start == guard.start and guard2.last_progress == guard.last_progress and guard2.turns == guard.turns and guard2.recent == guard.recent and guard2.diff == guard.diff and guard2.done_at == guard.done_at and guard2.calls_known == guard.calls_known,
    )

    # Test observe never raises on empty list
    clock = StubClock(now=0)
    guard = a.TaskGuard(clock=clock.time, calls_known=True)
    check(
        "observe never raises on empty list",
        guard.observe([], None) is None,
    )

    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())