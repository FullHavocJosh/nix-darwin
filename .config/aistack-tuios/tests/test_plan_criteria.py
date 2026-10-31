"""Test plan_criteria function."""

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
    check("plan_criteria(None) returns empty string", a.plan_criteria(None) == '')
    
    # Test with a prd with story
    prd = {
        "userStories": [
            {
                "id": "T1",
                "acceptanceCriteria": ["a", "b"]
            }
        ]
    }
    result = a.plan_criteria(prd)
    check("story criteria are included", "- T1: a" in result and "- T1: b" in result)
    
    # Test limit parameter
    result = a.plan_criteria(prd, limit=5)
    check("limit parameter works", len(result) == 5)
    
    # Test story with id 'T1'
    prd2 = {
        "userStories": [
            {
                "id": "T1", 
                "acceptanceCriteria": ["a"]
            }
        ]
    }
    result = a.plan_criteria(prd2)
    check("story with id 'T1' gives '- T1: a'", "- T1: a" in result)
    
    # Test load_review_diff is callable 
    check("load_review_diff is callable", callable(a.load_review_diff))
    
    print(f"\n{len(FAILS)} failures" if FAILS else "All tests pass!")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()