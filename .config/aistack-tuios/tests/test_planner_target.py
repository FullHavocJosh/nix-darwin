#!/usr/bin/env python3
"""The local plan pane runs on the TrashCan's 35B through the gateway when it can, else on the Mac mini's 9B."""

import json
import os
import sys
import tempfile
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import aidev_tuios as a
import planner_local as p


def check(name, cond, detail=""):
    if not cond:
        print(f"FAIL: {name} {detail}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: {name}")


KEY = "!python3 /x/gateway_key.py"
UP = {"trashcan": {"healthy": True, "window": 65536, "rank": 1, "model": "trash-plan"}}


def main():
    t = p.planner_target(UP, KEY)
    check("healthy TrashCan with a 65536 window is plan-local", t["name"] == "plan-local" and t["backend"] == "trashcan")
    check("it goes through the gateway as node-trashcan", t["model"] == "node-trashcan" and t["base_url"].endswith("/auto"))
    check("the window comes from the gateway", t["ctx"] == 65536)
    check("the key is a command, never a literal", t["api_key"] == KEY)

    for name, pool in (("an unreadable gateway", None), ("an empty pool", {}),
                       ("a down TrashCan", {"trashcan": {"healthy": False, "window": 65536}}),
                       ("a TrashCan window under 49152", {"trashcan": {"healthy": True, "window": 8192}})):
        f = p.planner_target(pool, KEY)
        check(f"{name} falls back to the Mac mini 9B", f["name"] == "plan-local-fallback" and f["backend"] == "macmini-m1"
              and f["base_url"] == "http://127.0.0.1:8080" and f["api_key"] == "sk-local")

    cfg = p.planner_models(t["base_url"], t["model"], t["ctx"], t["api_key"])
    prov = cfg["providers"]["planner"]
    check("provider baseUrl ends in /v1 after the gateway base", prov["baseUrl"] == "https://llm.rollet.family/auto/v1")
    check("provider carries the key command", prov["apiKey"] == KEY)
    check("old three-argument call keeps sk-local", p.planner_models("http://h:1", "m", 10)["providers"]["planner"]["apiKey"] == "sk-local")

    # local_planner_body writes models.json from the target and records it without the key
    with tempfile.TemporaryDirectory() as tmp:
        run = types.SimpleNamespace(project=tmp, plan_dir=tmp + "/plan", dir=tmp + "/run", id="r1", data={"panes": {}},
                                    save=lambda: None)
        for d in ("plan", "run", "pi-plan"):
            os.makedirs(os.path.join(tmp, d), exist_ok=True)
        a.gateway_pool = lambda: UP
        body = a.local_planner_body(run, {"pi_plan": tmp + "/pi-plan"}, "hi", False)
        models = json.load(open(os.path.join(tmp, "pi-plan", "models.json")))
        check("the pane model is planner/node-trashcan", "planner/node-trashcan" in body)
        check("models.json points at the gateway", models["providers"]["planner"]["baseUrl"].startswith("https://llm.rollet.family"))
        check("the target is recorded without the key", run.data["planner_target"]["name"] == "plan-local"
              and "api_key" not in run.data["planner_target"])
        a.gateway_pool = lambda: None
        a.local_planner_body(run, {"pi_plan": tmp + "/pi-plan"}, "hi", False)
        models = json.load(open(os.path.join(tmp, "pi-plan", "models.json")))
        check("without a gateway the pane uses the Mac mini 9B", models["providers"]["planner"]["baseUrl"] == "http://127.0.0.1:8080/v1")

    # the planners command
    a.gateway_pool = lambda: UP
    rows = a.planners_rows()
    check("planners lists plan-local then plan-billed", [r["id"] for r in rows] == ["plan-local", "plan-billed"])
    check("plan-local is online with the TrashCan speed", rows[0]["online"] is True and rows[0]["tg_tok_s"] == 7)
    check("plan-billed needs approval and is not probed", rows[1]["needs_approval"] is True and rows[1]["online"] is None)
    a.gateway_pool = lambda: None
    rows = a.planners_rows()
    check("plan-local reports its fallback when the TrashCan is unreachable", rows[0]["fallback"] is True and rows[0]["online"] is False)
    print("ALL PASS")


if __name__ == "__main__":
    main()
