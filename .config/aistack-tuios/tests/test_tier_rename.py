#!/usr/bin/env python3
"""Tests for the tier-id builder constants in aidev_tuios (BUILDERS, norm_kind, tier_of, RESET_CMD, next_tier).
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_tier_rename.py
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(os.path.dirname(ROOT), "aistack")  # this checkout's zen_models.py
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    for var in ("AIDEV_TUIOS_SESSION", "AIDEV_TUIOS_RUN", "AIDEV_TUIOS_PROJECT", "AIDEV_TUIOS_BUILDER",
                "AIDEV_SEMI_LOCAL", "AIDEV_SEMI_LOCAL_URL", "AIDEV_REMOTE_BUILDER_KEY_FILE",
                "AIDEV_REMOTE_BUILDER_URL", "AIDEV_HOST_RAM_GB", "AIDEV_REMOTE_BUILDER"):
        os.environ.pop(var, None)
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_HOME"] = tmp
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    check("BUILDERS", a.BUILDERS == {"tier-0": "build-local-tier-0", "tier-1": "build-local-tier-1",
                                     "tier-2": "build-local-tier-2", "tier-3": "build-free-tier-3",
                                     "tier-4": "build-billed-tier-4"}, str(a.BUILDERS))
    check("norm_kind semi-local", a.norm_kind("semi-local") == "tier-2")
    check("norm_kind billed", a.norm_kind("billed") == "tier-4")
    check("norm_kind bogus", a.norm_kind("bogus") is None)
    check("tier_of old pane", a.tier_of("build-semi-local") == "tier-2")
    check("tier_of new pane", a.tier_of("build-free-tier-3") == "tier-3")
    check("RESET_CMD tier-4", a.RESET_CMD["tier-4"] == "/clear")
    check("next_tier tier-2", a.next_tier("tier-2", "available") == "tier-3")
    check("next_tier tier-2 no free", a.next_tier("tier-2", "none") == "tier-4")
    check("next_tier tier-0", a.next_tier("tier-0", "available") == "tier-3")
    check("next_tier tier-3", a.next_tier("tier-3", "available") == "tier-4")

    check("tier1_available off by default", a.tier1_available() is False)
    real = (a.semi_local_available, a.local_builder_available, a.tier1_available, a.zen_status, a.zen_usable)
    try:
        a.semi_local_available, a.local_builder_available = (lambda: True), (lambda: True)
        a.tier1_available = lambda: True
        a.zen_status, a.zen_usable = (lambda run, refresh=False: "available"), (lambda s: s == "available")
        check("tier_online tier-0", a.tier_online("tier-0") is True)
        check("tier_online tier-1 (disabled)", a.tier_online("tier-1") is False)
        check("tier_online tier-2", a.tier_online("tier-2") is True)
        check("tier_online tier-3", a.tier_online("tier-3") is True)
        check("tier_online tier-4", a.tier_online("tier-4") is True)
        check("tier_online bogus", a.tier_online("tier-9") is False)
        a.semi_local_available, a.local_builder_available = (lambda: False), (lambda: False)
        a.zen_status = lambda run, refresh=False: "none"
        check("tier_online tier-0 offline", a.tier_online("tier-0") is False)
        check("tier_online tier-2 offline", a.tier_online("tier-2") is False)
        check("tier_online tier-3 none", a.tier_online("tier-3") is False)
        check("tier_online tier-4 always", a.tier_online("tier-4") is True)
    finally:
        a.semi_local_available, a.local_builder_available, a.tier1_available, a.zen_status, a.zen_usable = real

    cfg = {"pi_build": os.path.join(tmp, "pi-build")}
    key = os.path.join(tmp, "key")
    with open(key, "w") as fh:
        fh.write("sk-test")
    real_key = a.semi_key_file
    a.semi_key_file = lambda: key
    try:
        for tid, prov in (("tier-1", "semi1"), ("tier-2", "semi")):
            model = a.write_build_pi(cfg, tid)
            with open(os.path.join(cfg["pi_build"], "models.json")) as fh:
                spec = json.load(fh)["providers"][prov]
            m = spec["models"][0]
            check(f"write_build_pi {tid} model", model == f"{prov}/{a.tier_alias(tid)}", model)
            check(f"write_build_pi {tid} baseUrl", spec["baseUrl"] == a.tier_url(tid), spec["baseUrl"])
            check(f"write_build_pi {tid} id", m["id"] == a.tier_alias(tid), m["id"])
            check(f"write_build_pi {tid} ctx", m["contextWindow"] == a.tiers()[tid]["ctx"], str(m["contextWindow"]))
    finally:
        a.semi_key_file = real_key
    why = a.no_builder_why("tier-1")
    check("no_builder_why tier-1", isinstance(why, str) and bool(why))

    print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
