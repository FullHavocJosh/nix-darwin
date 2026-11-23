#!/usr/bin/env python3
"""Test wait_builder_model: footer wait logic."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
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


# Mock sleep to track how many times it's called
SLEEPS = []


def mock_sleep(s):
    SLEEPS.append(s)


a.time.sleep = mock_sleep


def feed(lst):
    it = iter(lst)
    return lambda session, name, lines=15: next(it, lst[-1]) + "\n"


# Test case 1: unknown for 3 polls then the right model gives ok
SLEEPS.clear()
a.pane_text = feed(["", "", "", "(semi) qwen3-coder-30b"])
r = a.wait_builder_model('S', 'N', 'tier-2')
check("unknown for 3 polls then right model gives ok", r == (True, "") and len(SLEEPS) == 3)


# Test case 2: unknown past the wait gives not ok with message footer unknown after 10 s
SLEEPS.clear()
a.pane_text = feed([""] * 10)
r = a.wait_builder_model('S', 'N', 'tier-2')
check("unknown past the wait gives not ok with message footer unknown after 10 s", r == (False, "footer unknown after 10 s") and len(SLEEPS) == 10)


# Test case 3: wrong model refuses at once with no sleep
SLEEPS.clear()
a.pane_text = feed(["(coder) some-model"])
r = a.wait_builder_model('S', 'N', 'tier-2')
check("wrong model refuses at once with no sleep", r == (False, "coder/some-model") and len(SLEEPS) == 0)


# Test case 4: empty string is an empty pane, so builder_model_ok returns unknown
SLEEPS.clear()
a.pane_text = feed(["(semi) qwen3-coder-30b"])
r = a.wait_builder_model('S', 'N', 'tier-2')
check("empty string is an empty pane, so builder_model_ok returns unknown", r == (True, "") and len(SLEEPS) == 0)


sys.exit(1 if FAILS else 0)