#!/usr/bin/env python3
"""Test the loop stop: a builder that loops on its done phrase is interrupted and reset, and what turns it off."""

import contextlib
import importlib.util
import io
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []
BUILDER = "build-local"  # a BUILDERS value, so loop_stop finds its kind


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def loop_stop_case(screen, replied=False, state="idle", info=None):
    """loop_stop with a fake tuios showing `screen`; returns (result, tuios calls, resets, printed, events)."""
    calls, resets, events = [], [], []

    def fake_tuios(*args, **_kw):
        calls.append(args)
        return (0, screen, "") if args and args[0] == "capture-pane" else (0, "", "")

    def fake_reset_pane(_run, name, cmd):
        resets.append(("pane", name, cmd))
        return True

    def fake_reset_builder(_run, name):
        resets.append(("builder", name))
        return True

    a.tuios = fake_tuios
    a.agent_state = lambda *_args, **_kw: state
    a.agent_info = lambda *_args, **_kw: {} if info is None else info
    a.wait_rest = lambda *_args, **_kw: True
    a.loop_mail = lambda *_args, **_kw: False
    a.reset_pane = fake_reset_pane
    a.reset_builder = fake_reset_builder
    run = types.SimpleNamespace(session="s", event=lambda *_a, **k: events.append(k))
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        result = a.loop_stop(run, BUILDER, "T1", replied=replied)
    return result, calls, resets, printed.getvalue(), events


def main():
    real = {
        name: getattr(a, name)
        for name in (
            "tuios",
            "agent_state",
            "agent_info",
            "wait_rest",
            "loop_mail",
            "reset_pane",
            "reset_builder",
            "thread_replies",
            "tier_of",
            "time",
        )
    }
    a.time = types.SimpleNamespace(sleep=lambda s: None, time=time.time)
    looped = "I've successfully completed task T1\n" * 3
    once = "I've successfully completed task T1"

    result, calls, resets, printed, events = loop_stop_case(looped)
    check(
        "three phrases reset the pane",
        result is True and resets == [("pane", BUILDER, a.RESET_CMD["local"])],
        f"{result} {resets}",
    )
    check(
        "escape was sent",
        any(c and c[0] == "send-keys" and c[-1] == "escape" for c in calls),
    )
    check("the stop is printed", "looped on completion; reset" in printed, printed)
    check("one event is recorded", len(events) == 1, str(events))

    result, _calls, resets, _printed, _events = loop_stop_case(once)
    check(
        "one phrase without a reply resets the builder",
        result is True and resets == [("builder", BUILDER)],
        f"{result} {resets}",
    )

    result, _calls, resets, _printed, _events = loop_stop_case(once, replied=True)
    check(
        "one phrase with a reply does not stop",
        result is False and not resets,
        f"{result} {resets}",
    )

    result, _calls, resets, _printed, _events = loop_stop_case(
        "successfully completed task T2"
    )
    check(
        "another task's phrase does not stop",
        result is False and not resets,
        f"{result} {resets}",
    )

    saved = os.environ.get("AIDEV_TUIOS_LOOP_STOP")
    os.environ["AIDEV_TUIOS_LOOP_STOP"] = "off"
    try:
        result, calls, resets, printed, events = loop_stop_case(looped)
        check(
            "AIDEV_TUIOS_LOOP_STOP=off stops nothing",
            result is False and not calls and not resets and not printed and not events,
        )
    finally:
        if saved is None:
            os.environ.pop("AIDEV_TUIOS_LOOP_STOP", None)
        else:
            os.environ["AIDEV_TUIOS_LOOP_STOP"] = saved

    result, _calls, resets, _printed, _events = loop_stop_case(
        looped, state="needs_input", info={"blocked_by": "approval"}
    )
    check(
        "a builder waiting on approval is not stopped",
        result is False and not resets,
        f"{result} {resets}",
    )

    check(
        "completion_ids picks every task id",
        a.completion_ids(
            "I have successfully completed task t2. I've successfully completed task T10"
        )
        == ["T2", "T10"],
    )

    a.tuios = lambda *_args, **_kw: (0, "", "")
    a.tier_of = lambda *_args, **_kw: "local"
    a.thread_replies = lambda *_args, **_kw: []
    check(
        "wait_reply reports the loop",
        a.wait_reply("s", "me", "249", BUILDER, 5, on_poll=lambda: True)
        == ("looped", ""),
    )
    a.thread_replies = lambda *_args, **_kw: [(1, "build-local", "done")]
    check(
        "wait_reply prefers a real reply",
        a.wait_reply("s", "me", "249", BUILDER, 5, on_poll=lambda: True)
        == ("reply", "done"),
    )

    for name, value in real.items():
        setattr(a, name, value)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
