"""Tests that cmd_builder closes a builder pane that started in another work dir instead of reusing it. Needs no tuios
daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_builder_stale_pane.py
"""
import importlib.util
import inspect
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios

FAILS = []


def check(label, ok):
    print(("PASS " if ok else "FAIL ") + label)
    if not ok:
        FAILS.append(label)


def main():
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_DIR"] = os.path.realpath(os.path.join(ROOT, "..", "aistack"))
    a = load("aidev_tuios", os.path.join(ROOT, "aidev_tuios.py"))

    old = tempfile.mkdtemp(prefix="aidev-test-old-")
    new = tempfile.mkdtemp(prefix="aidev-test-new-")
    sub = os.path.join(new, "sub")
    os.mkdir(sub)

    check("pane in another work dir is stale", a.stale_builder_pane({"cwd": old}, new) is True)
    check("pane in the work dir is not stale", a.stale_builder_pane({"cwd": new}, new) is False)
    check("pane under the work dir is not stale", a.stale_builder_pane({"cwd": sub}, new) is False)
    check("pane whose cwd is gone is stale", a.stale_builder_pane({"cwd": "/no/such/dir"}, new) is True)
    check("pane without a cwd is not stale", a.stale_builder_pane({}, new) is False)

    src = inspect.getsource(a.cmd_builder)
    i, j = src.find("stale_builder_pane("), src.find("already open")
    check("cmd_builder checks for a stale pane before reusing it", 0 <= i < j)

    return 1 if FAILS else 0


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


if __name__ == "__main__":
    sys.exit(main())
