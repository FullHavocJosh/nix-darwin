"""Test the check_already_passes function."""

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def main():
    with tempfile.TemporaryDirectory() as d:
        # Test that check_already_passes returns True when all commands pass (exit 0)
        result = a.check_already_passes(['true'], d, os.path.join(d, 'test1.txt'))
        check("check_already_passes(['true']) is True", result is True, f"got {result}")
        
        # Test that check_already_passes returns False when any command fails (exit 1)
        result = a.check_already_passes(['false'], d, os.path.join(d, 'test2.txt'))
        check("check_already_passes(['false']) is False", result is False, f"got {result}")
        
        # Test that check_already_passes returns False when one command fails in a list
        result = a.check_already_passes(['true', 'false'], d, os.path.join(d, 'test3.txt'))
        check("check_already_passes(['true', 'false']) is False", result is False, f"got {result}")
        
        # Test that check_already_passes returns True when all commands pass in a list
        result = a.check_already_passes(['true', 'true'], d, os.path.join(d, 'test4.txt'))
        check("check_already_passes(['true', 'true']) is True", result is True, f"got {result}")
        
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())