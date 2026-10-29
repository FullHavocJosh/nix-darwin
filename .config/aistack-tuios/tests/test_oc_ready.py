#!/usr/bin/env python3
"""Test oc_ready: the OpenCode ready footer ('ctrl+p menu' without 'esc interrupt') counts as ready, and a pane that
is still working ('esc interrupt') does not. Needs no tuios daemon, no model and no network.
Run: python3 .config/aistack-tuios/tests/test_oc_ready.py
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


class Clock:
    """A fake a.time whose sleep advances the clock, so a timeout needs no real waiting."""

    def __init__(self):
        self.t = 1000.0

    def time(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def main():
    real_text, real_time = a.pane_text, a.time
    a.time = Clock()
    a.pane_text = lambda session, name, lines=15: "  opencode\n  ctrl+p menu  /help\n"
    check("ready footer is ready", a.oc_ready("s", "free") is True)
    a.pane_text = lambda session, name, lines=15: "  working...  esc interrupt\n  ctrl+p menu\n"
    check("interrupting pane is not ready", a.oc_ready("s", "free", wait=1) is False)
    a.pane_text = lambda session, name, lines=15: ""
    check("empty pane is not ready", a.oc_ready("s", "free", wait=1) is False)
    a.pane_text, a.time = real_text, real_time
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
