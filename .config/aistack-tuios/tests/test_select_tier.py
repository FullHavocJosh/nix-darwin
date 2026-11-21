#!/usr/bin/env python3
"""Test estimate_tokens, select_tier and next_tier_id in aidev_tiers.py."""

import copy
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tiers", os.path.join(HERE, "..", "aidev_tiers.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def tiers(**over):
    t = copy.deepcopy(mod.DEFAULTS)
    t['tier-1']['enabled'] = True
    for tid, o in over.items():
        t[tid.replace('_', '-')].update(o)
    return t


def st(**kw):
    """st(t1='idle'|'busy'|'off', ...) builds a state dict; unlisted tiers are absent (offline)."""
    out = {}
    for k, v in kw.items():
        out[k.replace('t', 'tier-')] = {'online': v != 'off', 'idle': v == 'idle'}
    return out


SMALL, LARGE = 12000, 20000

check("estimate_tokens", mod.estimate_tokens(3500, 4000) == 14000, str(mod.estimate_tokens(3500, 4000)))
check("estimate_tokens int", isinstance(mod.estimate_tokens(10, 10), int))

T = tiers()
sel = mod.select_tier
r = sel(SMALL, st(t1='idle', t2='idle'), T)
check("small, both idle -> tier-1", r[0] == 'tier-1' and r[1], str(r))
r = sel(LARGE, st(t1='idle', t2='idle'), T)
check("large, both idle -> tier-2", r[0] == 'tier-2', str(r))
r = sel(SMALL, st(t1='off', t2='idle'), T)
check("tier-1 offline -> tier-2", r[0] == 'tier-2', str(r))
r = sel(LARGE, st(t1='busy', t2='busy'), T)
check("both busy, large -> tier-2", r[0] == 'tier-2', str(r))
r = sel(SMALL, st(t1='busy', t2='busy'), T)
check("both busy, small -> tier-1", r[0] == 'tier-1', str(r))
r = sel(SMALL, st(t1='busy', t2='idle'), T)
check("tier-1 busy, tier-2 idle -> tier-2", r[0] == 'tier-2', str(r))
r = sel(LARGE, st(t1='idle', t2='idle'), T)
check("need above tier-1 ctx never tier-1", r[0] != 'tier-1', str(r))
r = sel(SMALL, st(t0='idle', t1='off', t2='off', t3='idle'), T)
check("both G14 offline -> tier-0", r[0] == 'tier-0', str(r))
r = sel(SMALL, {'tier-0': {'online': True, 'idle': True}}, T)
check("G14 state missing -> tier-0", r[0] == 'tier-0', str(r))
r = sel(40000, st(t0='idle', t1='off', t2='off', t3='idle'), T)
check("tier-0 too small -> tier-3", r[0] == 'tier-3', str(r))
r = sel(40000, st(t0='idle', t1='off', t2='off', t3='off'), T)
check("tier-3 offline -> tier-4", r[0] == 'tier-4', str(r))
r = sel(SMALL, {}, T)
check("empty state -> tier-4", r[0] == 'tier-4', str(r))
r = sel(70000, st(t1='idle', t2='idle', t3='idle'), T)
check("need above tier-2 ctx -> None, split", r[0] is None and 'split' in r[1], str(r))
r = sel(SMALL, st(t1='idle', t2='idle'), T, min_tier=2)
check("min_tier=2 skips tier-1", r[0] == 'tier-2', str(r))
r = sel(SMALL, st(t0='idle', t1='off', t2='off', t3='idle'), T, min_tier=3)
check("min_tier=3 skips tier-0", r[0] == 'tier-3', str(r))
r = sel(SMALL, st(t1='idle', t2='idle', t3='idle'), T, min_tier=4)
check("min_tier=4 -> tier-4", r[0] == 'tier-4', str(r))
r = sel(SMALL, st(t1='idle', t2='idle'), tiers(tier_1={'enabled': False}))
check("tier-1 disabled never chosen", r[0] == 'tier-2', str(r))
r = sel(SMALL, st(t0='idle', t1='idle', t2='idle', t3='idle'), tiers(tier_1={'enabled': False}, tier_2={'enabled': False}))
check("both G14 disabled -> tier-0", r[0] == 'tier-0', str(r))

on = st(t1='idle', t2='idle', t3='idle')
nx = mod.next_tier_id
check("next tier-1 -> tier-2", nx('tier-1', on, T) == 'tier-2')
check("next tier-1, tier-2 offline -> tier-3", nx('tier-1', st(t1='idle', t2='off', t3='idle'), T) == 'tier-3')
check("next tier-1, tier-2 disabled -> tier-3", nx('tier-1', on, tiers(tier_2={'enabled': False})) == 'tier-3')
check("next tier-2 -> tier-3", nx('tier-2', on, T) == 'tier-3')
check("next tier-0 -> tier-3", nx('tier-0', on, T) == 'tier-3')
check("next tier-3 -> tier-4", nx('tier-3', on, T) == 'tier-4')
check("next tier-4 -> None", nx('tier-4', on, T) is None)
check("next unknown -> None", nx('tier-9', on, T) is None)
off3 = st(t1='idle', t2='idle', t3='off')
check("next tier-2, tier-3 offline -> tier-4", nx('tier-2', off3, T) == 'tier-4')
check("next tier-1, both off -> tier-4", nx('tier-1', st(t2='off', t3='off'), T) == 'tier-4')
check("next tier-0, tier-3 offline -> tier-4", nx('tier-0', off3, T) == 'tier-4')

if FAILS:
    print(f"FAIL: {len(FAILS)} failed")
    sys.exit(1)
print("PASS: all")
