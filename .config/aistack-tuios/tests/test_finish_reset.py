"""Test finish_reset_cmd (/clear or /compact after finish) and queue_plan_reset."""

import importlib.util
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py")
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


def make_run(tmp, statuses=("verified",)):
    tasks = {f"T{i}": {"status": s} for i, s in enumerate(statuses, 1)}
    return types.SimpleNamespace(
        data={"tasks": tasks}, plan_dir=tmp, session="s"
    )


def main():
    os.environ.pop("AIDEV_TUIOS_FINISH_RESET", None)
    with tempfile.TemporaryDirectory() as tmp:
        run = make_run(tmp)
        check(
            "all verified, clean, no followups gives /clear",
            a.finish_reset_cmd(run, False) == "/clear",
        )
        with open(os.path.join(tmp, "followups.txt"), "w") as f:
            f.write("  \n\n")
        check(
            "blank followups.txt gives /clear",
            a.finish_reset_cmd(run, False) == "/clear",
        )
        with open(os.path.join(tmp, "followups.txt"), "w") as f:
            f.write("do the thing\n")
        check(
            "non-blank followups.txt gives /compact",
            a.finish_reset_cmd(run, False).startswith("/compact"),
        )
        os.remove(os.path.join(tmp, "followups.txt"))
        check(
            "failed task gives /compact",
            a.finish_reset_cmd(make_run(tmp, ("verified", "failed")), False).startswith(
                "/compact"
            ),
        )
        check("dirty gives /compact", a.finish_reset_cmd(run, True).startswith("/compact"))
        os.environ["AIDEV_TUIOS_FINISH_RESET"] = "off"
        check("env off gives empty string", a.finish_reset_cmd(run, True) == "")
        os.environ.pop("AIDEV_TUIOS_FINISH_RESET", None)

    calls = []
    real_queue = a.queue
    a.queue = lambda *args: calls.append(args) or True
    run = types.SimpleNamespace(session="s")
    check("queue_plan_reset with empty cmd returns False", a.queue_plan_reset(run, "") is False)
    check("queue_plan_reset with empty cmd does not queue", calls == [])
    check("queue_plan_reset queues the command", a.queue_plan_reset(run, "/clear") is True)
    check("queue_plan_reset targets the plan pane", calls == [("s", a.PLAN, "/clear")], repr(calls))
    a.queue = real_queue
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
