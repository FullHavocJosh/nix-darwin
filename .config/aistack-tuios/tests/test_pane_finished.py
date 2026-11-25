#!/usr/bin/env python3
"""A build pane whose task is done is free: tier_state counts it idle and reset_builder stops it before /new. The node
tiers show model and GPU, not the hostname."""

import json
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import aidev_tiers as t
import aidev_tuios as a


def check(name, cond, detail=""):
    if not cond:
        print(f"FAIL: {name} {detail}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: {name}")


def run_with(tasks):
    events = []
    return types.SimpleNamespace(session="s", data={"tasks": tasks}, event=lambda *args, **kw: events.append(args), events=events)


def main():
    p4 = "build-local-tier-4"
    check("a pane with a task in progress is not finished", not a.pane_finished(run_with({"T1": {"builder": p4, "status": "sent"}}), p4))
    check("a pane whose task is verified is finished", a.pane_finished(run_with({"T1": {"builder": p4, "status": "verified"}}), p4))
    check("a pane whose task failed is finished", a.pane_finished(run_with({"T1": {"builder": p4, "status": "failed"}}), p4))
    check("a pane that never ran a task is not finished", not a.pane_finished(run_with({"T1": {"builder": "other", "status": "verified"}}), p4))
    check("one task done and one in progress on a pane is not finished",
          not a.pane_finished(run_with({"T1": {"builder": p4, "status": "verified"}, "T2": {"builder": p4, "status": "sent"}}), p4))

    # tier_state: a finished tier-4 pane that shows no ready footer is idle, so it beats an idle slower tier
    a.tier_online = lambda tid, run=None: True
    a.window_named = lambda session, name: True
    a.pane_idle = lambda session, name: False
    run = run_with({"T1": {"builder": p4, "status": "verified"}})
    st = a.tier_state(run)
    check("a finished tier-4 pane counts idle", st["tier-4"]["idle"] is True)
    check("a busy pane of another tier stays busy", st["tier-3"]["idle"] is False)
    tiers = t.DEFAULTS
    state = {k: {"online": True, "idle": v["idle"]} for k, v in st.items()}
    state["tier-2"]["idle"] = True
    tier, why = t.select_tier(1000, state, tiers)
    check("the finished tier-4 pane is picked over an idle tier-2", tier == "tier-4", (tier, why))

    # reset_builder stops a finished pane that is still working, then resets it
    keys, resets = [], []
    states = iter(["working", "working", "idle", "idle"])
    a.tuios = lambda *args, **kw: (keys.append(args[-1]), (0, "", ""))[1]
    a.agent_state = lambda session, name: next(states, "idle")
    a.wait_rest = lambda session, name, limit: True
    a.reset_pane = lambda run, builder, cmd: (resets.append(cmd), True)[1]
    run = run_with({"T1": {"builder": p4, "status": "verified"}})
    check("reset_builder succeeds on a finished pane that spins", a.reset_builder(run, p4) is True)
    check("it sent escape, then /new", keys[:1] == ["escape"] and resets == ["/new"], (keys, resets))
    check("it logged the stop", any(e[0] == "stop_finished_pane" for e in run.events))

    keys.clear(); resets.clear()
    states = iter(["idle"] * 4)
    a.reset_builder(run, p4)
    check("a finished pane already at rest is not interrupted", keys == [] and resets == ["/new"], (keys, resets))

    # labels: model and GPU, no hostname
    labels = {k: v["label"] for k, v in t.DEFAULTS.items() if k in t.NODE_TIERS}
    check("tier-4 label", labels["tier-4"] == "qwen3-coder-30B/Tier-4-4090", labels)
    check("tier-3 label", labels["tier-3"] == "qwen3.5-9B/Tier-3-4070", labels)
    check("no label names a host", not any(h in l.lower() for l in labels.values() for h in ("josh", "cait", "g14", "trashcan", "mac mini")), labels)

    # pi gets the label as the model display name; the id stays the gateway alias
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {"pi_build": tmp}
        a.semi_key_file = lambda: "/x/key"
        a.write_build_pi(cfg, "tier-4")
        models = json.load(open(os.path.join(tmp, "models.json")))["providers"]
        m = models["gw4"]["models"]
        check("gw4 lists the display name and keeps the alias id", m[0]["name"] == "qwen3-coder-30B/Tier-4-4090" and m[0]["id"] == "node-josh-g14", m[0])
        check("the thinking twin is named as such", m[1]["name"].endswith("(thinking)") and m[1]["id"] == "think-josh-g14", m[1])
    print("ALL PASS")


if __name__ == "__main__":
    main()
