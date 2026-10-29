"""Tests that send-task --to sends a task to that builder pane without switching the run's builder, and that the task
remembers its builder. Needs no tuios daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_send_to.py
"""
import importlib.util
import os
import sys
import tempfile
import types

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

    prd = {"name": "send-to", "description": "one task",
           "userStories": [{"id": "T1", "title": "a task", "description": "do it", "acceptanceCriteria": ["done"]}]}
    verify = {"T1": ["true"]}
    a.load_lib = lambda project=None, run=None: types.SimpleNamespace(load_plan=lambda project: (prd, verify, None))
    a.window_named = lambda session, name: True
    a.prepare_builder = lambda run, builder: True
    sent = []
    a.mail_task = lambda run, builder, subject, mail_text, prompt: sent.append(builder) or "7"
    a.snapshot_work = lambda run, label: None
    a.compaction_count = lambda session, builder: 0
    a.overflow_count = lambda session, builder: 0

    run = a.Run(p, "20260101-000001")
    run.data["session"] = "test"
    run.data["builder"] = "build-local"
    run.data["work_dir"] = p

    print("send-task T1 --to free")
    rc = a.cmd_send_task(run, ["T1", "--to", "free"])
    check("send-task returns 0", rc == 0, rc)
    check("the mail goes to build-free", sent == ["build-free"], sent)
    t = run.data["tasks"].get("T1") or {}
    check("the task remembers build-free", t.get("builder") == "build-free", t.get("builder"))
    check("the run's builder is unchanged", run.data.get("builder") == "build-local", run.data.get("builder"))

    print("an unknown kind is a usage error")
    check("send-task --to nope returns 2", a.cmd_send_task(run, ["T1", "--to", "nope"]) == 2)

    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
