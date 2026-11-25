#!/usr/bin/env python3
"""Test aidev_tiers.py has tier-7 and tier-8 in TIER_IDS and DEFAULTS with the right labels and pane names."""

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


# Check TIER_IDS ends with tier-7, tier-8
check("TIER_IDS ends with tier-7, tier-8", 
      mod.TIER_IDS[-2:] == ('tier-7', 'tier-8'), 
      str(mod.TIER_IDS))

# Check DEFAULTS has tier-7 with given pane name and label
tier7_defaults = mod.DEFAULTS['tier-7']
check("tier-7 pane is 'build-zen-tier-7'", 
      tier7_defaults['pane'] == 'build-zen-tier-7', 
      f"got {tier7_defaults['pane']!r}")
check("tier-7 label is 'OpenCode Zen'", 
      tier7_defaults['label'] == 'OpenCode Zen', 
      f"got {tier7_defaults['label']!r}")
check("tier-7 kind is 'opencode'", 
      tier7_defaults['kind'] == 'opencode', 
      f"got {tier7_defaults['kind']!r}")
check("tier-7 ctx is 0", 
      tier7_defaults['ctx'] == 0, 
      f"got {tier7_defaults['ctx']!r}")
check("tier-7 enabled is False", 
      tier7_defaults['enabled'] == False, 
      f"got {tier7_defaults['enabled']!r}")

# Check DEFAULTS has tier-8 with given pane name and label
tier8_defaults = mod.DEFAULTS['tier-8']
check("tier-8 pane is 'build-openrouter-tier-8'", 
      tier8_defaults['pane'] == 'build-openrouter-tier-8', 
      f"got {tier8_defaults['pane']!r}")
check("tier-8 label is 'OpenRouter'", 
      tier8_defaults['label'] == 'OpenRouter', 
      f"got {tier8_defaults['label']!r}")
check("tier-8 kind is 'pi'", 
      tier8_defaults['kind'] == 'pi', 
      f"got {tier8_defaults['kind']!r}")
check("tier-8 ctx is 0", 
      tier8_defaults['ctx'] == 0, 
      f"got {tier8_defaults['ctx']!r}")
check("tier-8 enabled is False", 
      tier8_defaults['enabled'] == False, 
      f"got {tier8_defaults['enabled']!r}")

# Check tier-5 label is 'OpenCode Go'
tier5_defaults = mod.DEFAULTS['tier-5']
check("tier-5 label is 'OpenCode Go'", 
      tier5_defaults['label'] == 'OpenCode Go', 
      f"got {tier5_defaults['label']!r}")


def st(**kw):
    """st(t1='idle'|'busy'|'off', ...) builds a state dict; unlisted tiers are absent (offline)."""
    out = {}
    for k, v in kw.items():
        out[k.replace('t', 'tier-')] = {'online': v != 'off', 'idle': v == 'idle'}
    return out


# Test _usable: tier-7 and tier-8 are not usable when state has no entry
state_empty = {}
check("_usable(tier-7, empty state) is False", 
      not mod._usable('tier-7', state_empty, mod.DEFAULTS, 0), 
      f"got {mod._usable('tier-7', state_empty, mod.DEFAULTS, 0)!r}")
check("_usable(tier-8, empty state) is False", 
      not mod._usable('tier-8', state_empty, mod.DEFAULTS, 0), 
      f"got {mod._usable('tier-8', state_empty, mod.DEFAULTS, 0)!r}")


# Test _usable: tier-7 and tier-8 become usable when state has online entry
state_t7_online = {'tier-7': {'online': True}}
check("_usable(tier-7, state with online entry) is True", 
      mod._usable('tier-7', state_t7_online, mod.DEFAULTS, 0), 
      f"got {mod._usable('tier-7', state_t7_online, mod.DEFAULTS, 0)!r}")
state_t8_online = {'tier-8': {'online': True}}
check("_usable(tier-8, state with online entry) is True", 
      mod._usable('tier-8', state_t8_online, mod.DEFAULTS, 0), 
      f"got {mod._usable('tier-8', state_t8_online, mod.DEFAULTS, 0)!r}")


# Test that cloud tiers (5-8) don't need enabled flag when state has online entry
state_t7_online_no_enabled = {'tier-7': {'online': True, 'enabled': False}}
check("_usable(tier-7, enabled=False but online) is True", 
      mod._usable('tier-7', state_t7_online_no_enabled, mod.DEFAULTS, 0), 
      f"got {mod._usable('tier-7', state_t7_online_no_enabled, mod.DEFAULTS, 0)!r}")


if FAILS:
    print(f"FAIL: {len(FAILS)} failed")
    sys.exit(1)
print("PASS: all")
