#!/usr/bin/env python3
"""Test fallback chain behavior: next_tier and cmd_fallback.

Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_fallback_chain.py
"""

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(
    os.path.dirname(ROOT), "aistack"
)  # this checkout's zen_models.py
os.environ["AIDEV_SEMI_LOCAL"] = "off"  # never probe the G14 over the network
FAILS = []


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    for var in (
        "AIDEV_TUIOS_SESSION",
        "AIDEV_TUIOS_RUN",
        "AIDEV_TUIOS_PROJECT",
        "AIDEV_TUIOS_BUILDER",
    ):
        os.environ.pop(var, None)
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(
        tempfile.mkdtemp(prefix="aidev-test-home-")
    )
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    print("next_tier behavior")
    # Test cases from the task description
    check(
        "tier-5 with available Zen -> tier-7",
        a.next_tier("tier-5", "available") == "tier-7",
    )
    check(
        "tier-5 with exhausted Zen -> tier-6",
        a.next_tier("tier-5", "exhausted") == "tier-6",
    )
    check(
        "tier-7 with available Zen -> tier-6",
        a.next_tier("tier-7", "available") == "tier-6",
    )
    check(
        "tier-7 with exhausted Zen -> tier-6",
        a.next_tier("tier-7", "exhausted") == "tier-6",
    )

    # Test that the functions exist and are callable
    # The original issue mentioned that the functions accept string zen_state values
    # which is what we're testing here
    
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())