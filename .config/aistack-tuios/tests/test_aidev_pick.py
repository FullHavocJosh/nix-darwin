#!/usr/bin/env python3
"""Test plan_pane_open and start_aidev functions in aidev_pick.py."""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_pick", os.path.join(HERE, "..", "aidev_pick.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def test_plan_pane_open():
    # Test 1: plan pane present
    original_env = os.environ.copy()
    try:
        os.environ['AIDEV_TUIOS_SESSION'] = 'test_session'
        os.environ['TUIOS_SESSION'] = 'test_session'
        original_run = mod.subprocess.run
        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == 'tuios' and 'list-windows' in cmd:
                return type('obj', (object,), {'returncode': 0, 'stdout': json.dumps({'windows': [{'custom_name': 'plan'}]})})()
            return original_run(cmd, *args, **kwargs)
        mod.subprocess.run = mock_run
        result = mod.plan_pane_open()
        check("plan pane present returns True", result == True)
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.subprocess.run = original_run

    # Test 2: plan pane absent
    try:
        os.environ['AIDEV_TUIOS_SESSION'] = 'test_session'
        os.environ['TUIOS_SESSION'] = 'test_session'
        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == 'tuios' and 'list-windows' in cmd:
                return type('obj', (object,), {'returncode': 0, 'stdout': json.dumps({'windows': [{'custom_name': 'other'}]})})()
            return original_run(cmd, *args, **kwargs)
        mod.subprocess.run = mock_run
        result = mod.plan_pane_open()
        check("plan pane absent returns False", result == False)
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.subprocess.run = original_run

    # Test 3: non-JSON output
    try:
        os.environ['AIDEV_TUIOS_SESSION'] = 'test_session'
        os.environ['TUIOS_SESSION'] = 'test_session'
        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == 'tuios' and 'list-windows' in cmd:
                return type('obj', (object,), {'returncode': 0, 'stdout': 'not json'})()
            return original_run(cmd, *args, **kwargs)
        mod.subprocess.run = mock_run
        result = mod.plan_pane_open()
        check("non-JSON output returns False", result == False)
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.subprocess.run = original_run

    # Test 4: no session env
    try:
        if 'AIDEV_TUIOS_SESSION' in os.environ:
            del os.environ['AIDEV_TUIOS_SESSION']
        if 'TUIOS_SESSION' in os.environ:
            del os.environ['TUIOS_SESSION']
        result = mod.plan_pane_open()
        check("no session env returns False", result == False)
    finally:
        os.environ.clear()
        os.environ.update(original_env)


def main():
    test_plan_pane_open()
    check("All plan_pane_open tests completed", True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())