#!/usr/bin/env python3
"""Test the max_output_tokens function and write_build_pi output."""

import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..")
os.environ['AIDEV_TIERS_FILE'] = os.path.join(tempfile.gettempdir(), 'aidev_tiers_test.json')
spec = importlib.util.spec_from_file_location("aidev_tiers", os.path.join(SRC, "aidev_tiers.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(SRC, "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


# Test defaults: tier-0 4096, tier-1 8192, tier-2 8192
check("defaults tier-0", mod.max_output_tokens("tier-0") == 4096, str(mod.max_output_tokens("tier-0")))
check("defaults tier-1", mod.max_output_tokens("tier-1") == 8192, str(mod.max_output_tokens("tier-1")))
check("defaults tier-2", mod.max_output_tokens("tier-2") == 8192, str(mod.max_output_tokens("tier-2")))

# Test tier-5 and tier-6 are 0 (from DEFAULTS)
check("tier-5 is 0", mod.max_output_tokens("tier-5") == 0, str(mod.max_output_tokens("tier-5")))
check("tier-6 is 0", mod.max_output_tokens("tier-6") == 0, str(mod.max_output_tokens("tier-6")))

# Test override file via AIDEV_TIERS_FILE in a temp dir changes tier-1
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'tiers.json')
    os.environ['AIDEV_TIERS_FILE'] = p
    try:
        with open(p, 'w') as f:
            json.dump({'tier-1': {'max_tokens': 16384}}, f)
        # max_output_tokens uses DEFAULTS by default, but we need to pass tiers() to see the override
        check("override tier-1", mod.max_output_tokens("tier-1", mod.load_tiers()) == 16384, str(mod.max_output_tokens("tier-1", mod.load_tiers())))
    finally:
        os.environ.pop('AIDEV_TIERS_FILE', None)

# Test write_build_pi writes maxTokens 4096 for the coder model
with tempfile.TemporaryDirectory() as tmp:
    cfg = {"pi_build": tmp}
    model = a.write_build_pi(cfg, kind="tier-0")
    check("returns coder/ model", isinstance(model, str) and model.startswith("coder/"), repr(model))
    model_path = os.path.join(tmp, "models.json")
    with open(model_path) as f:
        data = json.load(f)
    coder_max = data["providers"]["coder"]["models"][0]["maxTokens"]
    check("coder maxTokens 4096", coder_max == 4096, str(coder_max))

# Test write_build_pi for tier-1 writes maxTokens 8192 for the tier-1 provider
with tempfile.TemporaryDirectory() as tmp:
    cfg = {"pi_build": tmp}
    model = a.write_build_pi(cfg, kind="tier-1")
    check("tier-1 returns gw1/ model", isinstance(model, str) and model == "gw1/node-trashcan", repr(model))
    model_path = os.path.join(tmp, "models.json")
    with open(model_path) as f:
        data = json.load(f)
    tier1_max = data["providers"]["gw1"]["models"][0]["maxTokens"]
    check("tier-1 provider maxTokens 8192", tier1_max == 8192, str(tier1_max))
    # Check that tier-2 provider is also written
    tier2_max = data["providers"]["gw2"]["models"][0]["maxTokens"]
    check("tier-2 provider maxTokens 8192", tier2_max == 8192, str(tier2_max))

# Test write_build_pi for tier-2 writes maxTokens 8192 for the tier-2 provider
with tempfile.TemporaryDirectory() as tmp:
    cfg = {"pi_build": tmp}
    model = a.write_build_pi(cfg, kind="tier-2")
    check("tier-2 returns semi/ model", isinstance(model, str) and model == "gw2/node-macmini-m1", repr(model))
    model_path = os.path.join(tmp, "models.json")
    with open(model_path) as f:
        data = json.load(f)
    tier2_max = data["providers"]["gw2"]["models"][0]["maxTokens"]
    check("tier-2 provider maxTokens 8192", tier2_max == 8192, str(tier2_max))
    # Check that tier-1 provider is also written
    tier1_max = data["providers"]["gw1"]["models"][0]["maxTokens"]
    check("tier-1 provider maxTokens 8192", tier1_max == 8192, str(tier1_max))

sys.exit(1 if FAILS else 0)
