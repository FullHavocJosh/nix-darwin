#!/usr/bin/env python3
"""The local plan pane runs on this host's own 9B (32 GB or more), else on the Mac mini through the gateway; the TrashCan
never plans."""

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
MINI = {"healthy": True, "window": 65536, "rank": 2, "roles": ["plan"], "model": "qwen3.5-9b"}
TRASH = {"healthy": True, "window": 65536, "rank": 1, "roles": ["build"], "model": "trash-plan"}
UP = {"macmini-m1": MINI, "trashcan": TRASH}


def main():
    real_own_server = p.own_server
    p.own_server = lambda *a, **k: None  # the tests must not depend on this host's llama-server

    t = p.planner_target(UP, KEY)
    check("the plan node is the Mini through auto-plan", t["name"] == "plan-local" and t["backend"] == "macmini-m1"
          and t["model"] == "auto-plan" and t["base_url"].endswith("/auto"), t)
    check("the window comes from the gateway", t["ctx"] == 65536)
    check("the key is a command, never a literal", t["api_key"] == KEY)

    only_trash = p.planner_target({"trashcan": TRASH}, KEY)
    check("the TrashCan never plans, even when it is the only node up",
          only_trash["name"] == "plan-local-fallback" and only_trash["backend"] != "trashcan", only_trash)

    # before the gateway reports roles the Mini is addressed by its node pin
    old = p.planner_target({"macmini-m1": {"healthy": True, "window": 65536, "rank": 2}}, KEY)
    check("a gateway without roles uses the Mini's node pin", old["name"] == "plan-local" and old["model"] == "node-macmini-m1", old)

    for name, pool in (("an unreadable gateway", None), ("an empty pool", {}),
                       ("a down Mini", {"macmini-m1": dict(MINI, healthy=False)}),
                       ("a Mini window under 49152", {"macmini-m1": dict(MINI, window=8192)})):
        f = p.planner_target(pool, KEY)
        check(f"{name} falls back to the Mini's own 9B", f["name"] == "plan-local-fallback" and f["backend"] == "macmini-m1"
              and f["base_url"] == "http://127.0.0.1:8080" and f["api_key"] == "sk-local" and f["ctx"] == 65536, f)

    # a second plan node: the highest rank wins and the gateway keeps choosing through auto-plan
    two = p.planner_target({"macmini-m1": MINI, "macbook-m2pro": dict(MINI, rank=3)}, KEY)
    check("the highest-ranked plan node is reported", two["backend"] == "macbook-m2pro" and two["model"] == "auto-plan", two)

    OWN = {"healthy": True, "ctx": 131072, "ram_gb": 32}
    o = p.planner_target(UP, KEY, own=OWN)
    check("a 32 GB host with its own 9B plans on it, ahead of the Mini", o["name"] == "plan-local" and o["backend"] == "local-9b"
          and o["base_url"] == "http://127.0.0.1:8080" and o["ctx"] == 131072 and o["api_key"] == "sk-local", o)
    for name, own in (("a 16 GB host", dict(OWN, ram_gb=16)), ("an own window under 49152", dict(OWN, ctx=32768)),
                      ("an unhealthy own server", dict(OWN, healthy=False)), ("no own server", None)):
        check(f"{name} keeps the Mini", p.planner_target(UP, KEY, own=own)["backend"] == "macmini-m1")
    small = p.planner_target(None, KEY, own=dict(OWN, ram_gb=16, ctx=32768))
    check("the fallback takes the window the Mini serves", small["name"] == "plan-local-fallback" and small["ctx"] == 32768, small)
    check("own_server is None when nothing answers", real_own_server("http://127.0.0.1:1", timeout=1) is None)

    class R:
        def __init__(self, d):
            self.d = d

        def __enter__(self):
            return self

        def __exit__(self, *e):
            return False

        def read(self, *args):
            return json.dumps(self.d).encode()
    srv = real_own_server(ram_gb=32, opener=lambda u, timeout: R({"default_generation_settings": {"n_ctx": 131072}}))
    check("own_server reads the window from /props", srv == {"healthy": True, "ctx": 131072, "ram_gb": 32})

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
        check("the pane model is planner/auto-plan", "planner/auto-plan" in body)
        check("models.json points at the gateway", models["providers"]["planner"]["baseUrl"].startswith("https://llm.rollet.family"))
        check("the target is recorded without the key", run.data["planner_target"]["name"] == "plan-local"
              and "api_key" not in run.data["planner_target"])
        a.gateway_pool = lambda: None
        a.local_planner_body(run, {"pi_plan": tmp + "/pi-plan"}, "hi", False)
        models = json.load(open(os.path.join(tmp, "pi-plan", "models.json")))
        check("without a gateway the pane uses the Mini's own 9B", models["providers"]["planner"]["baseUrl"] == "http://127.0.0.1:8080/v1")

    # the planners command
    a.gateway_pool = lambda: UP
    rows = a.planners_rows()
    check("planners lists plan-local then plan-billed", [r["id"] for r in rows] == ["plan-local", "plan-billed"])
    check("plan-local is online on the Mini with the Mini's speed", rows[0]["online"] is True and rows[0]["backend"] == "macmini-m1"
          and rows[0]["tg_tok_s"] == 6, rows[0])
    check("plan-billed needs approval and is not probed", rows[1]["needs_approval"] is True and rows[1]["online"] is None)
    a.gateway_pool = lambda: None
    rows = a.planners_rows()
    check("plan-local reports its fallback when the gateway is unreachable", rows[0]["fallback"] is True and rows[0]["online"] is False)
    print("ALL PASS")


if __name__ == "__main__":
    main()
