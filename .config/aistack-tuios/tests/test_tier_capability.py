#!/usr/bin/env python3
"""Tests for capability-aware tier use: live gateway windows, fit_rows, the fit helper, size_problems picking a larger
online window, and the extra fields of the tiers output.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_tier_capability.py
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.environ["AISTACK_DIR"] = os.path.join(os.path.dirname(ROOT), "aistack")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    sys.path.insert(0, ROOT)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def story(desc, **extra):
    return {"userStories": [dict({"id": "T1", "title": "t", "description": desc, "acceptanceCriteria": ["ok"]}, **extra)]}


def main():
    t = load("aidev_tiers", os.path.join(ROOT, "aidev_tiers.py"))
    cfg = t.load_tiers()
    up = {tid: {"online": True} for tid in t.TIER_IDS}
    # fit_rows: a 20K prompt fits tier-2 (65536) and not tier-1 (4096 by default)
    rows, best, why = t.fit_rows(20000, 800, cfg, up)
    r = {x["id"]: x for x in rows}
    check("tier-1 too small for 20K at its default window", r["tier-1"]["fits"] is False)
    check("tier-2 fits 20K", r["tier-2"]["fits"] is True and r["tier-2"]["headroom"] > 0.25)
    check("best is the tier with the shortest est_s that fits", best == "tier-2", (best, why))
    # a tight fit is flagged and not preferred when another has room
    rows, best, why = t.fit_rows(60000, 800, cfg, up)
    check("60K of 65536 leaves under 25%: still tier-2 but flagged", best == "tier-2" and "under 25%" in why, why)
    # nothing local fits: a cloud tier takes it, else split
    rows, best, why = t.fit_rows(90000, 800, cfg, up)
    check("over every local window goes to tier-5", best == "tier-5", (best, why))
    off = dict(up, **{"tier-5": {"online": False}, "tier-6": {"online": False}})
    rows, best, why = t.fit_rows(90000, 800, cfg, off)
    check("no online tier fits means split", best is None and why.startswith("split"), (best, why))
    # the largest window wins when no speed is known
    custom = json.loads(json.dumps(cfg))
    custom["tier-1"]["ctx"] = 131072
    rows, best, _ = t.fit_rows(20000, 800, custom, up, speed={})
    check("without a speed table the larger window wins", best == "tier-1", best)

    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))
    a.tier_online = lambda tid, run=None: tid in ("tier-1", "tier-2")
    a.gateway_pool = lambda: {"trashcan": {"healthy": True, "window": 32768, "rank": 2, "model": "m"},
                              "josh-g14": {"healthy": True, "window": 65536, "rank": 4, "model": "m"}}
    live = a.tiers_live()
    check("tiers_live takes the gateway window", live["tier-1"]["ctx"] == 32768 and live["tier-2"]["ctx"] == 65536)
    a.gateway_pool = lambda: None
    check("tiers_live keeps the configured ctx without a gateway", a.tiers_live()["tier-1"]["ctx"] == 4096)

    # size_problems: a story too big for the smallest online window fits the larger one
    a.tiers = lambda: {"tier-0": {"ctx": 32768, "enabled": True}, "tier-1": {"ctx": 16384, "enabled": True},
                       "tier-2": {"ctx": 65536, "enabled": True}}
    big = "x" * 4000  # over the 16384 window's limit, within the 65536 window's
    check("story that fits only the bigger online tier is not a problem",
          a.size_problems(story(big), ctx=16384) == [])
    a.tier_online = lambda tid, run=None: tid == "tier-1"
    over = a.size_problems(story(big), ctx=16384)
    check("with the bigger tier offline the story is reported", len(over) == 1 and "16384" in over[0], over)
    a.tier_online = lambda tid, run=None: tid in ("tier-1", "tier-2")
    huge = "x" * 40000
    over = a.size_problems(story(huge), ctx=16384)
    check("a story over every window says the largest is too small",
          len(over) == 1 and "largest online window, 65536" in over[0], over)

    # tiers output: capability fields
    a.tiers = lambda: t.load_tiers()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        a.cmd_tiers(None, ["--json"])
    rows = {x["id"]: x for x in json.loads(buf.getvalue())}
    check("tiers json keeps ctx and adds room, model, thinking and speed",
          rows["tier-2"]["ctx"] == 65536 and rows["tier-2"]["room"] == 65536 - 12000
          and rows["tier-2"]["model"] == "qwen3-coder-30b" and rows["tier-2"]["thinking"] == "off"
          and rows["tier-2"]["tg_tok_s"] == 47 and rows["tier-5"]["room"] is None, rows["tier-2"])

    # fit helper
    run = types.SimpleNamespace(project=os.getcwd())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = a.cmd_fit(run, ["--chars", "3000", "--out", "500"])
    out = buf.getvalue()
    check("fit prints the need, every tier and a verdict", rc == 0 and "need about" in out and "tier-2" in out
          and "fits with" in out, out)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = a.cmd_fit(run, ["--bogus"])
    check("fit rejects unknown arguments", rc == 2)

    print("\nALL PASSED" if not FAILS else "\n%d FAILED" % len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
