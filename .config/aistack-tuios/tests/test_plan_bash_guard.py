#!/usr/bin/env python3
"""
Test cases for plan_bash_guard.py
"""

import subprocess
import sys


def test_bash_guard():
    # Test cases that should be denied
    deny_cases = [
        'grep -n foo x.txt',
        'ls | grep x',
        'find . -name x'
    ]
    
    # Test cases that should be allowed (silent)
    allow_cases = [
        'rg -n foo x.txt',
        'fd x',
        'git grep foo',
        'python3 tool explore "where is grep used"'
    ]
    
    # Test non-Bash tool (should be allowed)
    non_bash_case = {
        "tool_name": "Python",
        "tool_input": {
            "command": "print('hello')"
        }
    }
    
    FAILS = 0
    
    # Test cases that should be denied
    for case in deny_cases:
        result = subprocess.run([
            sys.executable, 
            '.config/aistack-tuios/plan_bash_guard.py'
        ], 
        input=f'{{"tool_name": "Bash", "tool_input": {{"command": "{case}"}}}}',
        text=True, 
        capture_output=True)
        
        if result.returncode != 0:
            print(f"FAIL: Denied case '{case}' failed with return code {result.returncode}")
            FAILS += 1
        elif 'permissionDecision": "deny"' not in result.stdout:
            print(f"FAIL: Denied case '{case}' was not denied")
            FAILS += 1
        else:
            print(f"PASS: Denied case '{case}' correctly denied")
    
    # Test cases that should be allowed (silent)
    for case in allow_cases:
        result = subprocess.run([
            sys.executable, 
            '.config/aistack-tuios/plan_bash_guard.py'
        ], 
        input=f'{{"tool_name": "Bash", "tool_input": {{"command": "{case}"}}}}',
        text=True, 
        capture_output=True)
        
        if result.returncode != 0:
            print(f"FAIL: Allowed case '{case}' failed with return code {result.returncode}")
            FAILS += 1
        elif result.stdout.strip() != '':
            print(f"FAIL: Allowed case '{case}' produced output when it should be silent")
            FAILS += 1
        else:
            print(f"PASS: Allowed case '{case}' correctly silent")
    
    # Test non-Bash tool
    result = subprocess.run([
        sys.executable, 
        '.config/aistack-tuios/plan_bash_guard.py'
    ], 
    input=str(non_bash_case),
    text=True, 
    capture_output=True)
    
    if result.returncode != 0:
        print(f"FAIL: Non-Bash case failed with return code {result.returncode}")
        FAILS += 1
    elif result.stdout.strip() != '':
        print("FAIL: Non-Bash case produced output when it should be silent")
        FAILS += 1
    else:
        print("PASS: Non-Bash case correctly silent")
    
    return FAILS

if __name__ == "__main__":
    FAILS = test_bash_guard()
    sys.exit(1 if FAILS else 0)