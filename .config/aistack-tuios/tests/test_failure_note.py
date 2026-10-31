#!/usr/bin/env python3
"""Test for failure_note function."""

import importlib.util
import sys

# Load aidev_tuios module
spec = importlib.util.spec_from_file_location("aidev_tuios", ".config/aistack-tuios/aidev_tuios.py")
aidev_tuios = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aidev_tuios)

def check():
    # Test the failure_note function
    attempt = 2
    out_path = "/tmp/test_output.txt"
    text = "HEAD" * 20 + "B" * 3420 + "C" * 1500  # 5000 characters
    
    result = aidev_tuios.failure_note(attempt, out_path, text)
    
    # Check that it contains 'Attempt 2'
    if "Attempt 2" not in result:
        print("FAIL: result does not contain 'Attempt 2'")
        return False
    
    # Check that it contains the out path
    if out_path not in result:
        print("FAIL: result does not contain the output path")
        return False
    
    # Check that it ends with the last 1500 characters of the text
    expected_last_part = text[-1500:].strip()
    if not result.endswith(f"\n{expected_last_part}"):
        print("FAIL: result does not end with the last 1500 characters of text")
        return False
    
    # Check that it does not contain the first characters of the text
    if text[:100] in result:
        print("FAIL: result contains the first characters of text")
        return False
    
    return True

FAILS = []

try:
    if not check():
        FAILS.append("failure_note test failed")
except Exception as e:
    FAILS.append(f"failure_note test error: {e}")

sys.exit(1 if FAILS else 0)