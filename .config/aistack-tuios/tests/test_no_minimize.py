#!/usr/bin/env python3
"""Regression test: ensure --minimize and minimize_window are not used in aidev_tuios.py."""

import os
import sys

# Get the repo root (4 levels up from this test file)
repo_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

FILES = [
    ".config/aistack-tuios/aidev_tuios.py",
    ".zsh_functions/tuios/10-devlayout.zsh",
]

def main():
    failures = []
    for filepath in FILES:
        full_path = os.path.join(repo_root, filepath)
        try:
            with open(full_path, "r") as f:
                content = f.read()
            if "--minimize" in content:
                failures.append(f"File {filepath} contains '--minimize'")
            if "minimize_window" in content:
                failures.append(f"File {filepath} contains 'minimize_window'")
        except Exception as e:
            failures.append(f"Could not read {filepath}: {e}")
    
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        sys.exit(1)
    
    print("PASS: No --minimize or minimize_window found")
    return 0

if __name__ == "__main__":
    sys.exit(main())