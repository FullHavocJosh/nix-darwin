"""Tests that two helpers saving the same run state.json merge instead of overwriting each other: task updates from
both survive, and a top-level key changed by one is not dropped by the other's save. Needs no tuios daemon, no model
and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_state_merge.py
"""
import importlib.util
import os
import sys
import tempfile

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


def main():
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_DIR"] = os.path.realpath(os.path.join(ROOT, "..", "aistack"))
    a = load("aidev_tuios", os.path.join(ROOT, "aidev_tuios.py"))
    p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))
    run_id = "20260101-000001"

    print("seed the run")
    seed = a.Run(p, run_id)
    seed.data["tasks"] = {"T1": {"id": "T1", "status": "todo"}, "T2": {"id": "T2", "status": "todo"}}
    seed.save()
    check("the state file exists", os.path.isfile(seed.path), seed.path)
    check("the state file holds the seed tasks", sorted(a.rj(seed.path, {}).get("tasks", {})) == ["T1", "T2"],
          a.rj(seed.path, {}).get("tasks"))

    print("two helpers change different tasks")
    one = a.Run(p, run_id)
    two = a.Run(p, run_id)
    one.data["tasks"]["T1"] = {"id": "T1", "status": "done"}
    one.data["note"] = "from one"
    one.save()
    two.data["tasks"]["T2"] = {"id": "T2", "status": "done"}
    two.save()

    print("a fresh read has both")
    fresh = a.Run(p, run_id)
    check("helper one's task survives", fresh.data["tasks"].get("T1") == {"id": "T1", "status": "done"},
          fresh.data["tasks"].get("T1"))
    check("helper two's task survives", fresh.data["tasks"].get("T2") == {"id": "T2", "status": "done"},
          fresh.data["tasks"].get("T2"))
    check("a top-level key set by one survives the other's save", fresh.data.get("note") == "from one",
          fresh.data.get("note"))
    check("untouched top-level keys are kept", fresh.data.get("run_id") == run_id, fresh.data.get("run_id"))

    print("the merge also holds in memory")
    check("the second saver sees the merged state", two.data.get("note") == "from one", two.data.get("note"))

    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
