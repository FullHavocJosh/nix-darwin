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
    timeouts = []
    answers = ["no"]

    def fake_ask(session, question, options, timeout_s=None):
        asked.append(question)
        timeouts.append(timeout_s)
        return answers[0]

    a.ask_human = fake_ask

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
    check("the ask is capped at BILLED_ASK_TIMEOUT_S", timeouts == [a.BILLED_ASK_TIMEOUT_S], timeouts)

    print("builder billed, no Inbox answer")
    answers[0] = ""
    rc = a.cmd_builder(run, ["billed"])
    check("returns 3 so the plan pane asks in chat", rc == 3, rc)

    print("builder billed, AIDEV_BILLED_ASK_TIMEOUT_S")
    os.environ["AIDEV_BILLED_ASK_TIMEOUT_S"] = "7"
    check("env value is used", a.billed_ask_timeout_s() == 7)
    os.environ["AIDEV_BILLED_ASK_TIMEOUT_S"] = "x"
    check("invalid value falls back", a.billed_ask_timeout_s() == a.BILLED_ASK_TIMEOUT_S)
    os.environ["AIDEV_BILLED_ASK_TIMEOUT_S"] = "0"
    check("non-positive falls back", a.billed_ask_timeout_s() == a.BILLED_ASK_TIMEOUT_S)
    del os.environ["AIDEV_BILLED_ASK_TIMEOUT_S"]

    print("builder (auto) with only billed left")
    a.auto_builder = lambda run: "billed"
    before = len(asked)
    rc = a.cmd_builder(run, [])
    check("returns 3 without an Inbox ask", rc == 3 and len(asked) == before, (rc, asked))
    rc = a.cmd_builder(run, ["--approved"])
    check("auto with --approved opens billed", rc == 0 and len(asked) == before, (rc, asked))

    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
