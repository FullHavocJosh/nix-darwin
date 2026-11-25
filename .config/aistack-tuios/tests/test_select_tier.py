#!/usr/bin/env python3
"""Test estimate_tokens, select_tier and next_tier_id in aidev_tiers.py."""

import copy
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tiers", os.path.join(HERE, "..", "aidev_tiers.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def tiers(**over):
    t = copy.deepcopy(mod.DEFAULTS)
    t["tier-1"]["enabled"] = True
    for tid, o in over.items():
        t[tid.replace("_", "-")].update(o)
    return t


def st(**kw):
    """st(t1='idle'|'busy'|'off', ...) builds a state dict; unlisted tiers are absent (offline)."""
    out = {}
    for k, v in kw.items():
        out[k.replace("t", "tier-")] = {"online": v != "off", "idle": v == "idle"}
    return out


SMALL, LARGE = 12000, 20000

check(
    "estimate_tokens",
    mod.estimate_tokens(3500, 4000) == 14000,
    str(mod.estimate_tokens(3500, 4000)),
)
check("estimate_tokens int", isinstance(mod.estimate_tokens(10, 10), int))

T = tiers(tier_1={"ctx": 16384})
sel = mod.select_tier
r = sel(SMALL, st(t1="idle", t2="idle"), T)
check("small, both idle -> tier-2 (fastest first)", r[0] == "tier-2" and r[1], str(r))
r = sel(LARGE, st(t1="idle", t2="idle"), T)
check("large, both idle -> tier-2", r[0] == "tier-2", str(r))
r = sel(SMALL, st(t1="off", t2="idle"), T)
check("tier-1 offline -> tier-2", r[0] == "tier-2", str(r))
r = sel(LARGE, st(t1="busy", t2="busy"), T)
check("both busy, large -> tier-2", r[0] == "tier-2", str(r))
r = sel(SMALL, st(t1="busy", t2="busy"), T)
check("both busy, small -> tier-2 (fastest first)", r[0] == "tier-2", str(r))
r = sel(SMALL, st(t1="busy", t2="idle"), T)
check("tier-1 busy, tier-2 idle -> tier-2", r[0] == "tier-2", str(r))
r = sel(LARGE, st(t1="idle", t2="idle"), T)
check("need above tier-1 ctx never tier-1", r[0] != "tier-1", str(r))
r = sel(SMALL, st(t0="idle", t1="off", t2="off", t5="idle"), T)
check("both G14 offline -> tier-5, not tier-0", r[0] == "tier-5", str(r))
r = sel(SMALL, {"tier-0": {"online": True, "idle": True}}, T)
check("G14 state missing -> tier-0", r[0] == "tier-0", str(r))
r = sel(40000, st(t0="idle", t1="off", t2="off", t5="idle"), T)
check("tier-0 too small -> tier-5", r[0] == "tier-5", str(r))
r = sel(40000, st(t0="idle", t1="off", t2="off", t5="off"), T)
check("tier-5 offline -> tier-6", r[0] == "tier-6", str(r))
r = sel(40000, st(t0="idle", t1="off", t2="off", t5="off", t7="idle"), T)
check("tier-7 online -> tier-7", r[0] == "tier-7", str(r))
r = sel(40000, st(t0="idle", t1="off", t2="off", t5="off", t7="off", t6="idle"), T)
check("tier-6 online -> tier-6", r[0] == "tier-6", str(r))
r = sel(
    40000, st(t0="idle", t1="off", t2="off", t5="off", t7="off", t6="off", t8="idle"), T
)
check("tier-8 picked when tier-6 offline", r[0] == "tier-8", str(r))
r = sel(
    40000,
    st(t0="idle", t1="off", t2="off", t5="off", t7="off", t6="idle", t8="idle"),
    T,
)
check("tier-8 skipped when tier-6 online", r[0] == "tier-6", str(r))
r = sel(SMALL, st(t1="off", t2="off", t5="off", t7="idle", t6="idle"), T)
check("tier-7 before tier-6", r[0] == "tier-7", str(r))
r = sel(
    SMALL, st(t0="idle", t1="off", t2="off", t5="off", t7="off", t6="off", t8="off"), T
)
check("only tier-0 online -> tier-0", r[0] == "tier-0", str(r))
r = sel(SMALL, {}, T)
check("empty state -> tier-6", r[0] == "tier-6", str(r))
r = sel(70000, st(t1="idle", t2="idle", t5="idle"), T)
check("need above tier-2 ctx -> None, split", r[0] is None and "split" in r[1], str(r))
r = sel(SMALL, st(t1="idle", t2="idle"), T, min_tier=2)
check("min_tier=2 skips tier-1", r[0] == "tier-2", str(r))
r = sel(SMALL, st(t0="idle", t1="off", t2="off", t5="idle"), T, min_tier=5)
check("min_tier=5 skips tier-0", r[0] == "tier-5", str(r))
r = sel(SMALL, st(t1="idle", t2="idle", t5="idle"), T, min_tier=6)
check("min_tier=6 -> tier-6", r[0] == "tier-6", str(r))
r = sel(SMALL, st(t1="off", t2="off", t5="idle", t7="idle"), T, min_tier=6)
check("min_tier=6 skips tier-5 -> tier-7", r[0] == "tier-7", str(r))
r = sel(SMALL, st(t1="idle", t2="idle"), tiers(tier_1={"enabled": False}))
check("tier-1 disabled never chosen", r[0] == "tier-2", str(r))
r = sel(
    SMALL,
    st(t0="idle", t1="idle", t2="idle", t5="idle"),
    tiers(tier_1={"enabled": False}, tier_2={"enabled": False}),
)
check("both G14 disabled -> tier-5", r[0] == "tier-5", str(r))

on = st(t1="idle", t2="idle", t5="idle")
nx = mod.next_tier_id
check("next tier-1 -> tier-5 (free cloud first)", nx("tier-1", on, T) == "tier-5")
check(
    "next tier-1, tier-0 online -> tier-5 (tier-0 is last)",
    nx("tier-1", st(t0="idle", t1="idle", t2="idle", t5="idle"), T) == "tier-5",
)
check(
    "next tier-1, tier-2 offline -> tier-5",
    nx("tier-1", st(t1="idle", t2="off", t5="idle"), T) == "tier-5",
)
check(
    "next tier-1, tier-2 disabled -> tier-5",
    nx("tier-1", on, tiers(tier_2={"enabled": False})) == "tier-5",
)
check("next tier-2 -> tier-1", nx("tier-2", on, T) == "tier-1")
check(
    "next tier-2, tier-1 off -> tier-5",
    nx("tier-2", st(t1="off", t2="idle", t5="idle"), T) == "tier-5",
)
check(
    "next tier-2, tier-1 off, tier-0 on -> tier-5",
    nx("tier-2", st(t0="idle", t1="off", t2="idle", t5="idle"), T) == "tier-5",
)
check("next tier-0 -> None", nx("tier-0", on, T) is None)
check(
    "next tier-5, tier-7 online -> tier-7",
    nx("tier-5", st(t1="idle", t2="idle", t5="idle", t7="idle"), T) == "tier-7",
)
check("next tier-5, tier-7 offline -> tier-6", nx("tier-5", on, T) == "tier-6")
check(
    "next tier-5, tier-7 and tier-6 off -> tier-6",
    nx("tier-5", st(t5="idle"), T) == "tier-6",
)
check("next tier-7 -> tier-6", nx("tier-7", on, T) == "tier-6")
check(
    "next tier-6, tier-8 online -> tier-8",
    nx("tier-6", st(t6="idle", t8="idle"), T) == "tier-8",
)
check("next tier-6, tier-8 offline -> None", nx("tier-6", on, T) is None)
check("next tier-8 -> None", nx("tier-8", st(t8="idle"), T) is None)
check("next unknown -> None", nx("tier-9", on, T) is None)
off3 = st(t1="idle", t2="idle", t5="off")
check("next tier-2, tier-5 offline -> tier-1", nx("tier-2", off3, T) == "tier-1")
check(
    "next tier-2, tier-1 and tier-5 offline -> None",
    nx("tier-2", st(t1="off", t2="idle", t5="off"), T) is None,
)
check(
    "next tier-1, both off -> None",
    nx("tier-1", st(t2="off", t5="off"), T) is None,
)
check("next tier-0, tier-5 offline -> None", nx("tier-0", off3, T) is None)
check(
    "next tier-4, tier-5 off, tier-7 on -> tier-7",
    nx("tier-4", st(t7="idle"), T) == "tier-7",
)
check(
    "next tier-4, tier-5/7 off, tier-6 on -> tier-6",
    nx("tier-4", st(t6="idle"), T) == "tier-6",
)
check(
    "next tier-4, tier-6 off, tier-8 on -> tier-8",
    nx("tier-4", st(t8="idle"), T) == "tier-8",
)
check(
    "next tier-4, tier-6 on beats tier-8 -> tier-6",
    nx("tier-4", st(t6="idle", t8="idle"), T) == "tier-6",
)
check(
    "next tier-4, all cloud off, tier-0 on -> tier-0",
    nx("tier-4", st(t0="idle"), T) == "tier-0",
)
check("next tier-4, all off -> None", nx("tier-4", {}, T) is None)

if FAILS:
    print(f"FAIL: {len(FAILS)} failed")
    sys.exit(1)
print("PASS: all")
