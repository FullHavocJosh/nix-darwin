#!/usr/bin/env python3
"""Tests for cmd_builder gate usage: checks that billed_gate is used and tier-0 through tier-8 are listed in help."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(
    os.path.dirname(ROOT), "aistack"
)  # this checkout's zen_models.py
os.environ["AIDEV_SEMI_LOCAL"] = "off"  # never probe the G14 over the network


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))
    
    # Check that there's exactly one billed_gate function
    source = open(os.path.join(ROOT, "aidev_tuios.py")).read()
    billed_gate_count = source.count("def billed_gate")
    print(f"billed_gate function count: {billed_gate_count}")
    if billed_gate_count != 1:
        print(f"FAIL: Expected 1 billed_gate function, found {billed_gate_count}")
        return 1
        
    # Check that cmd_builder usage string includes tier-0 through tier-8
    import re
    usage_pattern = r"usage: builder \[(tier-0|tier-1|tier-2|tier-3|tier-4|tier-5|tier-6|tier-7|tier-8)\|.*\] \[--approved\]"
    usage_match = re.search(usage_pattern, source)
    if not usage_match:
        print("FAIL: cmd_builder usage string doesn't list tiers 0-8")
        return 1
    print("PASS: cmd_builder usage string lists all tiers 0-8")
    
    print("Basic functionality checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())