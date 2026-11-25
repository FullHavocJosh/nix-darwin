"""Tests that mail_task drains the builder's unread mail before sending. Needs no tuios daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_mail_drain.py
"""
import importlib.util
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

    run = types.SimpleNamespace(session="s")

    recorded = []
    a.tuios = lambda *args: recorded.append(args) or (0, "message 9 queued for build (x)", "")
    a.deliver_prompt = lambda *args: None
    a.mail_id = lambda out: "9"

    print("mail_task should drain older mail first")
    result = a.mail_task(run, "build-x", "task T1", "body", "prompt @@MID@@")

    check("result is 9", result == "9", result)
    check("first call is read-agent-messages", len(recorded) >= 1 and recorded[0][0] == "read-agent-messages", recorded)
    check("first call has -s s", len(recorded) >= 1 and recorded[0][1] == "-s", recorded)
    check("first call has -w build-x", len(recorded) >= 1 and recorded[0][3] == "-w", recorded)
    check("first call has build-x", len(recorded) >= 1 and recorded[0][4] == "build-x", recorded)
    check("first call has --unread", len(recorded) >= 1 and recorded[0][5] == "--unread", recorded)
    check("second call starts with send-agent-message", len(recorded) >= 2 and recorded[1][0] == "send-agent-message", recorded)

    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS)))
    return 1 if FAILS else 0


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    global FAILS
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


if __name__ == "__main__":
    FAILS = []
    sys.exit(main())
