#!/usr/bin/env python3
"""Tests for aidev's builder chain logic (auto_builder, next_tier). Tests all four scenarios from the task description.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_builder_chain.py
"""
import importlib.util
import io
import os
import sys
import tempfile
from contextlib import redirect_stdout

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
    # Clear environment variables that might interfere
    for var in ("AIDEV_TUIOS_SESSION", "AIDEV_TUIOS_RUN", "AIDEV_TUIOS_PROJECT", "AIDEV_TUIOS_BUILDER",
                "AIDEV_SEMI_LOCAL", "AIDEV_SEMI_LOCAL_URL", "AIDEV_REMOTE_BUILDER_KEY_FILE",
                "AIDEV_REMOTE_BUILDER_URL", "AIDEV_HOST_RAM_GB", "AIDEV_REMOTE_BUILDER"):
        os.environ.pop(var, None)
        
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_HOME"] = tmp
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))
    
    # Set up a fake run object for testing
    class FakeRun:
        def __init__(self, data=None):
            self.data = data or {}
    
    # Test scenario 1: gateway up (semi-local available) - should pick semi-local
    print("Scenario 1: Gateway up - semi-local")
    # Mock semi_local_available to return True (gateway up)
    original_semi_local_available = a.semi_local_available
    a.semi_local_available = lambda: True
    
    # Mock the other functions to return False to make sure it picks semi-local
    original_local_builder_available = a.local_builder_available
    original_zen_status = a.zen_status
    original_zen_usable = a.zen_usable
    
    a.local_builder_available = lambda: False
    a.zen_status = lambda run, refresh=False: {"state": "none", "model": None, "detail": "no key", "models": []}
    a.zen_usable = lambda s: False
    
    fake_run = FakeRun()
    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture):
        result = a.auto_builder(fake_run)
    output = stdout_capture.getvalue()
    
    check("gateway up: semi-local picked", result == "tier-2")
    # Restore original functions after scenario 1
    a.semi_local_available = original_semi_local_available
    
    # Test scenario 2: gateway down, AIDEV_HOST_RAM_GB=16, model file present, zen usable - should pick free
    print("Scenario 2: Gateway down, 16 GB RAM, model file present, zen usable - free")
    # Set up environment for 16 GB RAM and a fake model file
    os.environ["AIDEV_HOST_RAM_GB"] = "16"
    fake_coder_file = os.path.join(tmp, "coder-30b-file")
    with open(fake_coder_file, "w") as f:
        f.write("fake model content")
    
    a.CODER_FILE = fake_coder_file
    a.semi_local_available = lambda: False
    # DO NOT stub a.local_builder_available - let real gate run
    a.zen_status = lambda run, refresh=False: {"state": "available", "model": "test-model", "detail": "", "models": []}
    a.zen_usable = lambda s: True
    
    fake_run = FakeRun()
    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture):
        result = a.auto_builder(fake_run)
    output = stdout_capture.getvalue()
    
    check("gateway down, 16GB, model present, zen usable: free picked", result == "tier-3")
    check("output contains RAM info", "16 GB" in output)
    # Restore original function after scenario 2
    a.local_builder_available = original_local_builder_available
    
    # Test scenario 3: gateway down, AIDEV_HOST_RAM_GB=16, zen_status state 'none' with NO_ZEN_KEY detail - should pick billed
    print("Scenario 3: Gateway down, 16 GB RAM, no Zen key - billed")
    a.zen_status = lambda run, refresh=False: {"state": "none", "model": None, "detail": a.NO_ZEN_KEY, "models": []}
    a.zen_usable = lambda s: False
    
    fake_run = FakeRun()
    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture):
        result = a.auto_builder(fake_run)
    output = stdout_capture.getvalue()
    
    check("gateway down, 16GB, no zen key: billed picked", result == "tier-4")
    check("output contains OPENCODE_ZEN_API_KEY", "OPENCODE_ZEN_API_KEY" in output)
    
    # Test scenario 4: gateway down, AIDEV_HOST_RAM_GB=64, model file present - should pick local
    print("Scenario 4: Gateway down, 64 GB RAM, model file present - local")
    os.environ["AIDEV_HOST_RAM_GB"] = "64"
    a.semi_local_available = lambda: False
    # DO NOT stub a.local_builder_available - let real gate run
    a.zen_status = lambda run, refresh=False: {"state": "none", "model": None, "detail": "no key", "models": []}
    a.zen_usable = lambda s: False
    
    fake_run = FakeRun()
    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture):
        result = a.auto_builder(fake_run)
    output = stdout_capture.getvalue()
    
    check("gateway down, 64GB, model present: local picked", result == "tier-0")
    # Restore original function after scenario 4
    a.local_builder_available = original_local_builder_available
    
    # Test scenario 5: unready pane with gateway up - should skip semi-local
    print("Scenario 5: Unready pane with gateway up - should skip semi-local")
    a.semi_local_available = lambda: True
    a.local_builder_available = lambda: False
    a.zen_status = lambda run, refresh=False: {"state": "none", "model": None, "detail": "no key", "models": []}
    a.zen_usable = lambda s: False
    
    fake_run = FakeRun(data={"unready": ["tier-2"]})
    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture):
        result = a.auto_builder(fake_run)
    output = stdout_capture.getvalue()
    
    check("unready pane: semi-local skipped", result == "tier-4")
    check("skip message shown", "skip tier-2: its pane never became ready" in output)
    
    # Test scenario 6: next_tier order - semi-local->local->free->billed with variations
    print("Scenario 6: next_tier order tests")
    # Test next_tier function - based on the notes, need to use 'available' state so free is returned
    check("next_tier: tier-2 -> tier-3", a.next_tier("tier-2", "available") == "tier-3")
    check("next_tier: local -> free", a.next_tier("tier-0", "available") == "tier-3")
    check("next_tier: free -> billed", a.next_tier("tier-3", "available") == "tier-4")
    check("next_tier: billed -> None", a.next_tier("tier-4", "available") is None)
    
    # Test with local_ok=False should skip local
    check("next_tier: semi-local -> free (local skipped)", a.next_tier("tier-2", "available", False) == "tier-3")
    
    # Test with zen_state="exhausted" should skip free
    check("next_tier: tier-2 -> tier-4 (zen exhausted)", a.next_tier("tier-2", "exhausted", True) == "tier-4")
    
    # Test with zen_state="none" should skip free
    check("next_tier: local -> billed (free skipped, zen none)", a.next_tier("tier-0", "none") == "tier-4")
    
    # Restore original functions
    a.semi_local_available = original_semi_local_available
    a.local_builder_available = original_local_builder_available
    a.zen_status = original_zen_status
    a.zen_usable = original_zen_usable
    
    print(f"\n{'='*50}")
    if FAILS:
        print(f"FAILED: {len(FAILS)} test(s)")
        for fail in FAILS:
            print(f"  - {fail}")
        return 1
    else:
        print("All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())