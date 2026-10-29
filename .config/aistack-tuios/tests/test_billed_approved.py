"""Tests that `builder billed --approved` opens the billed builder without the ask_human question, and that plain
`builder billed` still asks. Needs no tuios daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_billed_approved.py
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

    asked = []
    a.window_named = lambda session, name: False
    a.start_builder = lambda run, kind, name, ws, cwd: (True, "ok")
    a.ask_human = lambda session, question, options: asked.append(question) or "no"

    run = a.Run(p, "20260101-000001")
    run.data["session"] = "test"
    run.data["work_dir"] = p

    print("builder billed --approved")
    rc = a.cmd_builder(run, ["billed", "--approved"])
    check("returns 0", rc == 0, rc)
    check("ask_human is not called", asked == [], asked)

    print("builder billed")
    rc = a.cmd_builder(run, ["billed"])
    check("ask_human is called", len(asked) == 1, asked)
    check("returns 1 when the user says no", rc == 1, rc)

    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
