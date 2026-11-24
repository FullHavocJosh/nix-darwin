#!/usr/bin/env python3
"""Test the preflight: send-task refuses a task whose prompt estimate plus output cap exceeds the tier window."""

import contextlib
import importlib.util
import io
import os
import sys
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


def send_task_case(need):
    """cmd_send_task --to tier-2 with stubs and a `need`-token task; returns (code, printed, mails, tasks, saves)."""
    mails, saves = [], []

    class FakeLib:
        def load_plan(self, _project):
            story = {"id": "T1", "title": "a task", "description": "d", "acceptanceCriteria": []}
            return {"userStories": [story]}, {"T1": {"cmds": ["true"]}}, "h"

    run = types.SimpleNamespace(
        session="s",
        project="p",
        dir="d",
        data={"builder": a.BUILDERS["tier-2"], "work_dir": "/w", "tasks": {}},
        event=lambda *_args, **_kw: None,
        save=lambda: saves.append(1),
    )
    real = {
        name: getattr(a, name)
        for name in (
            "research_gate",
            "window_named",
            "prepare_builder",
            "load_lib",
            "task_need",
            "tiers",
            "mail_task",
        )
    }
    a.research_gate = lambda _run: False
    a.window_named = lambda *_args, **_kw: True
    a.prepare_builder = lambda _run, _builder: True
    a.load_lib = lambda *_args, **_kw: FakeLib()
    a.task_need = lambda *_args, **_kw: need
    a.tiers = lambda: a.aidev_tiers.DEFAULTS
    a.mail_task = lambda *args, **_kw: mails.append(args) or 1
    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            code = a.cmd_send_task(run, ["T1", "--to", "tier-2"])
    finally:
        for name, value in real.items():
            setattr(a, name, value)
    return code, printed.getvalue(), mails, run.data["tasks"], saves


def main():
    g = a.aidev_guard
    check(
        "CONTEXT_WINDOW is the per-tier constant",
        g.CONTEXT_WINDOW == {"tier-0": 32768, "tier-1": 8192, "tier-2": 65536, "tier-3": 65536, "tier-4": 65536},
        str(g.CONTEXT_WINDOW),
    )
    ok, why = g.preflight("tier-2", 65536 - 8192, 8192)
    check("tier-2 at the boundary fits", ok and why == "", f"{ok} {why}")
    ok, why = g.preflight("tier-2", 65536 - 8192 + 1, 8192)
    check(
        "tier-2 one token over is refused with the split reason",
        not ok
        and why == "split: about 57345 prompt + 8192 output tokens exceed the 65536 window of tier-2",
        why,
    )
    ok, why = g.preflight("tier-0", 32768 - 4096, 4096)
    check("tier-0 with its 4096 cap at the boundary fits", ok and why == "", f"{ok} {why}")
    ok, why = g.preflight("tier-0", 32768 - 4096 + 1, 4096)
    check("tier-0 one token over is refused", not ok and "split" in why, why)
    ok, why = g.preflight("tier-5", 10 ** 9, 10 ** 9)
    check("tier-5 always fits", ok and why == "", f"{ok} {why}")
    ok, why = g.preflight("tier-6", 10 ** 9, 10 ** 9)
    check("tier-6 always fits", ok and why == "", f"{ok} {why}")
    ok, why = g.preflight(None, 10 ** 9, 10 ** 9)
    check("a pane without a tier fits", ok and why == "", f"{ok} {why}")
    ok, why = g.preflight("tier-9", 10 ** 9, 10 ** 9)
    check("an unknown tier fits", ok and why == "", f"{ok} {why}")

    code, printed, mails, tasks, saves = send_task_case(60000)
    check("send-task returns 1 when the task cannot fit", code == 1, str(code))
    check(
        "send-task prints the split reason",
        "split: about 60000 prompt + 8192 output tokens exceed the 65536 window of tier-2" in printed,
        printed,
    )
    check(
        "send-task sends nothing",
        mails == [] and tasks == {} and saves == [],
        f"{mails} {tasks} {saves}",
    )
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
