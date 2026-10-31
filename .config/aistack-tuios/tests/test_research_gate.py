#!/usr/bin/env python3
"""Test the research gate for the local planner and the ask-lumo cache."""

import importlib.util
import io
import json
import os
import sys
import tempfile
import types
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
import planner_local


def check(name, cond):
    if not cond:
        print(f"FAIL: {name}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: {name}")


def make_run(tmp, planner):
    run = types.SimpleNamespace(
        project=tmp, plan_dir=tmp, dir=os.path.join(tmp, "run"),
        data={"planner": planner, "panes": {a.RESEARCH: {"id": "x"}}}, events=[],
    )

    def event(kind, **kw):
        os.makedirs(run.dir, exist_ok=True)
        with open(os.path.join(run.dir, "events.jsonl"), "a") as fh:
            fh.write(json.dumps({"kind": kind, **kw}) + "\n")

    run.event = event
    return run


def call(fn, run, argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = fn(run, argv)
    return code, buf.getvalue()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        run = make_run(tmp, "local")
        code, out = call(a.cmd_check_plan, run, [])
        check("local planner without research is gated", code == 3 and "RESEARCH REQUIRED" in out)
        code, out = call(a.cmd_send_task, run, ["T1"])
        check("send-task is gated too", code == 3 and "RESEARCH REQUIRED" in out)
        code, out = call(a.cmd_ask_lumo, run, ["--none-needed"])
        check("empty waiver reason is a usage error", code == 2)
        code, out = call(a.cmd_ask_lumo, run, ["--none-needed", "repo only"])
        check("waiver recorded", code == 0 and "recorded: research waived (repo only)" in out)
        check("waiver lifts the gate", not a.research_gate(run))
    with tempfile.TemporaryDirectory() as tmp:
        run = make_run(tmp, "local")
        run.event("ask_lumo", searched=True)
        check("ask_lumo event lifts the gate", not a.research_gate(run))
    with tempfile.TemporaryDirectory() as tmp:
        run = make_run(tmp, "claude")
        check("claude planner is never gated", not a.research_gate(run))
    with tempfile.TemporaryDirectory() as tmp:
        run = make_run(tmp, "local")
        planner_local.cache_store(os.path.join(run.dir, "research"), "what is x?", "x is y", "q1")
        code, out = call(a.cmd_ask_lumo, run, ["what is x?"])
        check("cache hit is served", code == 0 and "x is y" in out and "saved Lumo note" in out)
        check("cache hit records an event", planner_local.read_events(run.dir)[-1].get("queries") == "cache")


main()
