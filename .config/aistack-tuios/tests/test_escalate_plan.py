#!/usr/bin/env python3
"""escalate-plan asks the user before any Claude plan pane; struggle hints appear after repeated failures; the Mini
fallback keeps the window its own server serves."""

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import aidev_tuios as a
import planner_local as p


def check(name, cond, detail=""):
    if not cond:
        print(f"FAIL: {name} {detail}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: {name}")


def make_run(planner="local", tasks=None, check_fails=0):
    events = []
    run = types.SimpleNamespace(
        id="r1", project="/p", plan_dir="/p/plan", dir="/p/run", session="s1",
        data={"planner": planner, "tasks": tasks or {}, "check_fails": check_fails, "panes": {"plan": {}}},
        event=lambda *args, **kw: events.append((args, kw)), save=lambda: None)
    run.events = events
    return run


def main():
    # the Mini fallback window
    down = p.planner_target(None, "")
    check("without an own server the Mini fallback is 65536", down["name"] == "plan-local-fallback" and down["ctx"] == 65536, down)
    small = p.planner_target(None, "", own={"healthy": True, "ctx": 32768, "ram_gb": 16})
    check("the fallback takes the window the Mini serves", small["ctx"] == 32768, small)

    # struggle signals
    check("a fresh run has no struggle reason", a.struggle_reasons(make_run()) == [])
    check("check-plan failing 3 times in a row is a struggle", len(a.struggle_reasons(make_run(check_fails=3))) == 1)
    check("two failures are not yet", a.struggle_reasons(make_run(check_fails=2)) == [])
    failed = {"T1": {"status": "failed", "attempts": 2}, "T2": {"status": "failed", "attempts": 2}}
    check("two tasks failed at their tier is a struggle", len(a.struggle_reasons(make_run(tasks=failed))) == 1)
    check("one failed task is not", a.struggle_reasons(make_run(tasks={"T1": failed["T1"]})) == [])
    check("a Claude plan pane never reports a struggle", a.struggle_reasons(make_run(planner="claude", check_fails=9)) == [])
    check("the hint names escalate-plan and the user's yes", "escalate-plan" in a.struggle_hint(make_run(check_fails=3))
          and "user" in a.struggle_hint(make_run(check_fails=3)))
    check("no hint when all is well", a.struggle_hint(make_run()) == "")

    # check-plan counts consecutive failures
    codes = iter([1, 1, 1, 0])
    a.next_commands_hint = lambda run: "next"
    a._check_plan = lambda run: next(codes)
    run = make_run()
    for _ in range(3):
        a.cmd_check_plan(run, [])
    check("three failed check-plans are counted", run.data["check_fails"] == 3, run.data)
    a.cmd_check_plan(run, [])
    check("a passing check-plan resets the count", run.data["check_fails"] == 0)

    # escalate-plan
    asked, popped = [], []
    a.write_script = lambda run, name, body: "/p/run/bin/plan.sh"
    a.claude_pane_body = lambda *args: "claude body"
    a.pane_configs = lambda project: {}
    a.window_named = lambda session, name: None
    a.subprocess.Popen = lambda *args, **kw: popped.append(args)

    def with_answer(code, out):
        a.tuios = lambda *args, **kw: (asked.append(args), (code, out, ""))[1]

    run = make_run()
    with_answer(0, "yes\n")
    rc = a.cmd_escalate_plan(run, ["check-plan keeps failing"])
    check("a yes switches the run to Claude and relaunches the pane", rc == 0 and run.data["planner"] == "claude" and len(popped) == 1, run.data)
    check("the ask names the reason and offers yes or no", asked[0][0] == "ask-human" and "check-plan keeps failing" in asked[0][1]
          and asked[0][2:6] == ("-o", "yes", "-o", "no"), asked[0])
    check("the question fits tuios's 160 byte limit", len(asked[0][1].encode()) <= 160, len(asked[0][1].encode()))
    check("the Claude launcher is stored for the relaunch", run.data["panes"]["plan"]["script"] == "/p/run/bin/plan.sh")

    popped.clear()
    run = make_run()
    with_answer(0, "no\n")
    check("a no keeps plan-local", a.cmd_escalate_plan(run, ["x"]) == 1 and run.data["planner"] == "local" and not popped)
    with_answer(2, "")
    run = make_run()
    check("no answer yet keeps plan-local and exits 3", a.cmd_escalate_plan(run, ["x"]) == 3 and run.data["planner"] == "local" and not popped)
    with_answer(1, "")
    check("a dismissed question keeps plan-local", a.cmd_escalate_plan(make_run(), ["x"]) == 1 and not popped)
    run = make_run(planner="claude")
    asked.clear()
    check("on Claude already: nothing is asked", a.cmd_escalate_plan(run, []) == 0 and not asked)
    check("escalate-plan is a helper", a.HELPERS["escalate-plan"] is a.cmd_escalate_plan)
    print("ALL PASS")


if __name__ == "__main__":
    main()
