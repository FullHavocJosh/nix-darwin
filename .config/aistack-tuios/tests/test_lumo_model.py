#!/usr/bin/env python3
"""Test for lumo_model_for function."""

import importlib.util
import os
import sys

# Load the module
spec = importlib.util.spec_from_file_location("aidev_tuios", "/Users/havoc/nix-darwin/.worktrees/aistack-aidev-local-planner-lumo-max-1122/.config/aistack-tuios/aidev_tuios.py")
aidev_tuios = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aidev_tuios)

def check(name, cond):
    if not cond:
        print(f"FAIL: {name}")
        sys.exit(1)
    print(f"PASS: {name}")

# Test that lumo_model_for function exists
check("lumo_model_for exists", hasattr(aidev_tuios, 'lumo_model_for'))

# Test that LUMO_MODEL is set correctly
check("LUMO_MODEL default", aidev_tuios.LUMO_MODEL == 'lumo-max')

# Test the function directly
# Test with no environment variable set
os.environ.pop('AISTACK_LUMO_MODEL', None)
check("lumo_model_for default behavior", aidev_tuios.lumo_model_for('http://test.com', 'test-key') == 'lumo-max')

print("All tests passed")