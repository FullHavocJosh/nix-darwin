"""Tests that a builder's queued tuios prompts are dropped before every stop and reset. Needs no tuios daemon, no model
and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_queue_drop.py
"""
import importlib.util
import inspect
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios


def main():
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_DIR"] = os.path.realpath(os.path.join(ROOT, "..", "aistack"))
    a = load("aidev_tuios", os.path.join(ROOT, "aidev_tuios.py"))

    recorded = []
    a.tuios = lambda *args: recorded.append(args) or (0, "new session", "")
    a.time.sleep = lambda *x: None
    a.agent_state = lambda *x: "idle"
    a.pane_finished = lambda *x: False
    a.agent_session_id = lambda *x: ""
    a.tier_of = lambda *x: "tier-4"
    run = types.SimpleNamespace(session="s", event=lambda *x, **k: None)

    print("reset_builder drops the queue first")
    a.reset_builder(run, "build-x")
    want = ("queue", "rm", "--all", "-s", "s", "-w", "build-x")
    check("first call is queue rm --all for build-x", len(recorded) >= 1 and recorded[0] == want, recorded[:2])

    print("guard_trip and loop_stop drop the queue before escape")
    for fn in (a.guard_trip, a.loop_stop):
        src = inspect.getsource(fn)
        drop, esc = src.find("drop_queue("), src.find('"escape"')
        check(f"{fn.__name__}: drop_queue( before escape", drop != -1 and esc != -1 and drop < esc, (drop, esc))

    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS)))
    return 1 if FAILS else 0


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FAILS = []

if __name__ == "__main__":
    sys.exit(main())
