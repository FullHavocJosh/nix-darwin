"""Test that task_prompt uses rg instead of grep."""

import importlib.util
import os
import sys

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
    result = a.task_prompt({'name':'n'}, {'id':'T1','title':'t','description':'d','acceptanceCriteria':['c']}, ['true'], [])
    
    check("Contains 'rg -n for the name'", "rg -n for the name" in result)
    check("Contains 'Search with rg'", "Search with rg" in result)
    check("Does not contain 'grep -n'", "grep -n" not in result)
    check("Contains 'Run the checks above yourself'", "Run the checks above yourself" in result)

    return len(FAILS)


if __name__ == "__main__":
    main()
    sys.exit(1 if FAILS else 0)