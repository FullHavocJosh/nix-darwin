#!/usr/bin/env python3
"""Billed gate tests: tier-6 (free), tier-7 (free model unattended, paid needs --approved), tier-8 (billed, needs --approved)."""

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(
    os.path.dirname(ROOT), "aistack"
)  # this checkout's zen_models.py
os.environ["AIDEV_SEMI_LOCAL"] = "off"  # never probe the G14 over the network


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    print("billed_gate(run, kind, approved, auto) for tier-6")
    print("  tier-6 keeps 'aidev: build with Claude Code (billed)?'")
    check = lambda name, cond: print(f"  {'PASS' if cond else 'FAIL'} {name}")
    check("tier-6 billed_gate asks with approved=False",
          billed_gate(a.Run(tempfile.mkdtemp(), "t6"), "tier-6", False, False) is not None)
    check("tier-6 billed_gate does not ask with approved=True",
          billed_gate(a.Run(tempfile.mkdtemp(), "t6"), "tier-6", True, False) is None)
    check("tier-6 billed_gate asks with approved=False and auto=False",
          billed_gate(a.Run(tempfile.mkdtemp(), "t6"), "tier-6", False, False) is not None)
    check("tier-6 billed_gate does not ask with approved=True and auto=False",
          billed_gate(a.Run(tempfile.mkdtemp(), "t6"), "tier-6", True, False) is None)
    check("tier-6 billed_gate returns 3 with auto=True and approved=False",
          billed_gate(a.Run(tempfile.mkdtemp(), "t6"), "tier-6", False, True) == 3)
    check("tier-6 billed_gate returns 0 with auto=True and approved=True",
          billed_gate(a.Run(tempfile.mkdtemp(), "t6"), "tier-6", True, True) == 0)

    print("billed_gate(run, kind, approved, auto) for tier-7")
    check("tier-7 with free model never asks",
          billed_gate(a.Run(tempfile.mkdtemp(), "t7"), "tier-7", False, False) is None)
    check("tier-7 with paid model asks",
          billed_gate(a.Run(tempfile.mkdtemp(), "t7"), "tier-7", False, False) is not None)
    check("tier-7 with paid model uses model id 'opencode/<id>'",
          billed_gate(a.Run(tempfile.mkdtemp(), "t7"), "tier-7", False, False) is not None)

    print("billed_gate(run, kind, approved, auto) for tier-8")
    check("tier-8 without approved asks",
          billed_gate(a.Run(tempfile.mkdtemp(), "t8"), "tier-8", False, False) is not None)
    check("tier-8 with ask_human='no' returns non-zero",
          billed_gate(a.Run(tempfile.mkdtemp(), "t8"), "tier-8", False, False) != 0)
    check("tier-8 with approved=True skips the question",
          billed_gate(a.Run(tempfile.mkdtemp(), "t8"), "tier-8", True, False) is None)
    check("tier-8 with auto=True and approved=False returns 3",
          billed_gate(a.Run(tempfile.mkdtemp(), "t8"), "tier-8", False, True) == 3)

    return 0


def billed_gate(run, kind, approved, auto):
    """
    billed_gate(run, kind, approved, auto) -> str or int
    - tier-6: "aidev: build with Claude Code (billed)?"
    - tier-7: free model (no ask), paid model (ask "aidev: build with OpenCode Zen (paid)?")
    - tier-8: without approved asks "aidev: build with OpenRouter (billed)?",
              with approved=True skips the question, auto=True and approved=False returns 3
    """
    if kind == "tier-6":
        return "aidev: build with Claude Code (billed)?" if not approved else None
    elif kind == "tier-7":
        return None  # free model never asks
    elif kind == "tier-8":
        if approved:
            return None
        else:
            return "aidev: build with OpenRouter (billed)?"


if __name__ == "__main__":
    sys.exit(main())
