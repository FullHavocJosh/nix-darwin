#!/usr/bin/env python3
"""Test the tier registry in aidev_tiers.py: aliases, tiers.json overrides, bad files, ctx limits."""

import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tiers", os.path.join(HERE, "..", "aidev_tiers.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


WORDS = {
    'tier-0': ['tier-0', 'tier0', '0', 'build-local-tier-0', 'build-local', 'local', '30b', ' 30B '],
    'tier-1': ['tier-1', 'tier1', '1', 'build-local-tier-1'],
    'tier-2': ['tier-2', 'tier2', '2', 'build-local-tier-2', 'build-semi-local', 'semi-local', 'semi', 'g14', 'G14'],
    'tier-5': ['tier-5', 'tier3', '3', 'build-free-tier-5', 'build-free', 'free', 'pickle'],
    'tier-6': ['tier-6', 'tier4', '4', 'build-billed-tier-6', 'build-billed', 'billed', 'claude', 'Claude'],
}
for tid, words in WORDS.items():
    for w in words:
        check(f"norm_tier({w!r}) == {tid}", mod.norm_tier(w) == tid, str(mod.norm_tier(w)))
for w in ('', 'tier-7', 'nope', None):
    check(f"norm_tier({w!r}) is None", mod.norm_tier(w) is None)

check("TIER_IDS", mod.TIER_IDS == ('tier-0', 'tier-1', 'tier-2', 'tier-5', 'tier-6'))
check("defaults ctx", [mod.DEFAULTS[t]['ctx'] for t in mod.TIER_IDS] == [32768, 4096, 65536, 0, 0])
check("tier-1 on by default", mod.DEFAULTS['tier-1']['enabled'] is True)
check("tier-1 alias default", mod.DEFAULTS['tier-1']['alias'] == 'trash-code')
check("tier-1 url default", mod.DEFAULTS['tier-1']['url'] == 'https://llm.rollet.family/trashcan/v1')

old_env = os.environ.get('AIDEV_TIERS_FILE')
try:
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'tiers.json')
        os.environ['AIDEV_TIERS_FILE'] = p
        check("tiers_path honors env", mod.tiers_path() == p)
        check("missing file gives defaults", mod.load_tiers() == mod.DEFAULTS)
        with open(p, 'w') as f:
            json.dump({'tier-1': {'enabled': True, 'ctx': 20000, 'bogus': 1},
                       'tier-2': {'ctx': 'big', 'enabled': 'yes', 'url': 5},
                       'tier-9': {'ctx': 1}}, f)
        t = mod.load_tiers()
        check("override ctx", t['tier-1']['ctx'] == 20000)
        check("override enabled", t['tier-1']['enabled'] is True)
        check("unknown key ignored", 'bogus' not in t['tier-1'])
        check("wrong types ignored", t['tier-2'] == mod.DEFAULTS['tier-2'])
        check("unknown tier ignored", 'tier-9' not in t)
        check("defaults untouched", mod.DEFAULTS['tier-1']['ctx'] == 4096 and mod.DEFAULTS['tier-1']['enabled'] is True)
        with open(p, 'w') as f:
            f.write('{not json')
        check("bad file gives defaults", mod.load_tiers() == mod.DEFAULTS)
        with open(p, 'w') as f:
            f.write('[1, 2]')
        check("non-dict file gives defaults", mod.load_tiers() == mod.DEFAULTS)
        check("explicit path arg", mod.load_tiers(os.path.join(d, 'none.json')) == mod.DEFAULTS)
finally:
    if old_env is None:
        os.environ.pop('AIDEV_TIERS_FILE', None)
    else:
        os.environ['AIDEV_TIERS_FILE'] = old_env

check("limits_for_ctx(65536)", mod.limits_for_ctx(65536) == {'max_read': 160608, 'max_chars': 4283, 'max_files': 3},
      str(mod.limits_for_ctx(65536)))
check("limits_for_ctx(0) is None", mod.limits_for_ctx(0) is None)

sys.exit(1 if FAILS else 0)
