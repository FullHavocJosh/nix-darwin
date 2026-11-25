#!/usr/bin/env python3
"""Tests for auto_builder order (tier-4, tier-5, tier-7, tier-0, tier-6).
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_auto_builder.py
"""

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.environ["AISTACK_DIR"] = os.path.join(os.path.dirname(ROOT), "aistack")
os.environ["AIDEV_SEMI_LOCAL"] = "off"
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
    # Clear environment variables that might interfere
    for var in (
        "AIDEV_TUIOS_SESSION",
        "AIDEV_TUIOS_RUN",
        "AIDEV_TUIOS_PROJECT",
        "AIDEV_TUIOS_BUILDER",
        "AIDEV_SEMI_LOCAL",
        "AIDEV_SEMI_LOCAL_URL",
        "AIDEV_SEMI_LOCAL_KEY_FILE",
        "AIDEV_REMOTE_BUILDER_KEY_FILE",
        "AIDEV_REMOTE_BUILDER_URL",
        "AIDEV_REMOTE_BUILDER",
        "AIDEV_HOST_RAM_GB",
    ):
        os.environ.pop(var, None)

    tmp = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_HOME"] = tmp
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    # Setup a fake run object
    class FakeRun:
        def __init__(self, data=None):
            self.data = data or {}
            self.project = os.environ.get("AIDEV_TUIOS_PROJECT") or os.getcwd()
            self.save = lambda: None

    print("auto_builder order tests")

    # Case 1: tier_online true for tier-4 gives tier-4
    print("Case 1: tier_online true for tier-4 gives tier-4")
    a.tier_online = lambda tid, run=None: tid == "tier-4"
    a.zen_status = lambda run, refresh=False, provider="go": {
        "state": "none",
        "model": None,
        "detail": "no key",
        "models": [],
    }
    a.zen_usable = lambda s: False
    a.local_builder_available = lambda: False

    fake_run = FakeRun(data={})
    result = a.auto_builder(fake_run)
    check("tier_online true for tier-4: tier-4 picked", result == "tier-4")

    # Case 2: nodes offline and tier-5 usable gives tier-5
    print("Case 2: nodes offline and tier-5 usable gives tier-5")
    a.tier_online = lambda tid, run=None: False  # all tier-1 to tier-4 offline
    a.zen_status = lambda run, refresh=False, provider="go": {
        "state": "available",
        "model": "node-josh-g14",
        "detail": "",
        "models": [],
    }
    a.zen_usable = lambda s: True
    a.local_builder_available = lambda: False

    fake_run = FakeRun(data={})
    result = a.auto_builder(fake_run)
    check("tier-5 usable, nodes offline: tier-5 picked", result == "tier-5")

    # Case 3: only a free bare-id Zen model gives tier-7
    print("Case 3: only a free bare-id Zen model gives tier-7")
    a.tier_online = lambda tid, run=None: False

    def zen_status_case3(run, refresh=False, provider="go"):
        if provider == "zen":
            return {
                "state": "available",
                "model": "big-pickle",
                "detail": "",
                "models": [],
            }
        return {"state": "none", "model": None, "detail": "no key", "models": []}

    a.zen_status = zen_status_case3
    a.zen_usable = lambda s: s["state"] in ("available", "unknown")
    a.local_builder_available = lambda: False

    fake_run = FakeRun(data={})
    result = a.auto_builder(fake_run)
    check("free bare-id Zen model: tier-7 picked", result == "tier-7")

    # Case 4: a paid opencode/ model skips tier-7
    print("Case 4: a paid opencode/ model skips tier-7")

    def zen_status_case4(run, refresh=False, provider="go"):
        if provider == "zen":
            return {
                "state": "available",
                "model": "opencode/some-paid",
                "detail": "",
                "models": [],
            }
        return {"state": "none", "model": None, "detail": "no key", "models": []}

    a.zen_status = zen_status_case4
    a.zen_usable = lambda s: s["state"] in ("available", "unknown")
    a.local_builder_available = lambda: False

    fake_run = FakeRun(data={})
    result = a.auto_builder(fake_run)
    check(
        "paid opencode model skips tier-7: tier-6 picked (no tier-0, no tier-5, no tier-4)",
        result == "tier-6",
    )

    # Case 5: nothing usable (tier_online false for every tier except tier-6) plus local_builder_available true gives tier-0
    print(
        "Case 5: nothing usable (tier_online false for every tier except tier-6) plus local_builder_available true gives tier-0"
    )
    a.tier_online = lambda tid, run=None: (
        tid == "tier-6"
    )  # only tier-6 is online, but tier-6 is last resort
    a.zen_status = lambda run, refresh=False, provider="go": {
        "state": "none",
        "model": None,
        "detail": "no key",
        "models": [],
    }
    a.zen_usable = lambda s: False
    a.local_builder_available = lambda: True

    fake_run = FakeRun(data={})
    result = a.auto_builder(fake_run)
    check(
        "local_builder_available true, tiers offline: tier-0 picked", result == "tier-0"
    )

    # Case 6: with local_builder_available false gives tier-6
    print("Case 6: with local_builder_available false gives tier-6")
    a.tier_online = lambda tid, run=None: tid == "tier-6"
    a.zen_status = lambda run, refresh=False, provider="go": {
        "state": "none",
        "model": None,
        "detail": "no key",
        "models": [],
    }
    a.zen_usable = lambda s: False
    a.local_builder_available = lambda: False

    fake_run = FakeRun(data={})
    result = a.auto_builder(fake_run)
    check(
        "no tier-0, no tier-5, no tier-4, no tier-7: tier-6 picked", result == "tier-6"
    )

    print()
    print(f"Ran {len([f for f in FAILS])} tests, {len(FAILS)} failed")
    for f in FAILS:
        print(f"  FAILED: {f}")

    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
