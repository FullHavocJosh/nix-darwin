#!/usr/bin/env python3
"""Test builder_model_ok: tier-1 or tier-2 panes must run on the expected provider."""

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


# Mock pane_text to return specific footers for testing
def mock_pane_text(footer):
    return lambda session, name, lines=15: footer + "\n"


# Test footer '(gw1) node-trashcan' ok for tier-1
a.pane_text = mock_pane_text("(gw1) node-trashcan")
check("(gw1) node-trashcan ok for tier-1", a.builder_model_ok(None, "free", "tier-1") == (True, ""))

# Test footer '(gw2) node-macmini-m1' ok for tier-2
a.pane_text = mock_pane_text("(gw2) node-macmini-m1")
check("(gw2) node-macmini-m1 ok for tier-2", a.builder_model_ok(None, "free", "tier-2") == (True, ""))

# Test footer '(openrouter) moonshotai/kimi-k2.7-code' not ok for tier-2 and shown names it
a.pane_text = mock_pane_text("(openrouter) moonshotai/kimi-k2.7-code")
check("(openrouter) moonshotai/kimi-k2.7-code not ok for tier-2", a.builder_model_ok(None, "free", "tier-2") == (False, "openrouter/moonshotai/kimi-k2.7-code"))

# Test unparsable footer is not ok for tier-1 (strict mode)
a.pane_text = mock_pane_text("unparsable footer")
check("unparsable footer not ok for tier-1 (strict)", a.builder_model_ok(None, "free", "tier-1", strict=True) == (False, "unknown"))

# Test unparsable footer is ok for tier-1 (non-strict mode)
a.pane_text = mock_pane_text("unparsable footer")
check("unparsable footer ok for tier-1 (non-strict)", a.builder_model_ok(None, "free", "tier-1", strict=False) == (True, ""))

# Test empty footer is not ok for tier-1
a.pane_text = mock_pane_text("")
check("empty footer not ok for tier-1", a.builder_model_ok(None, "free", "tier-1") == (False, "unknown"))

# Test footer '(coder) some-model' not ok for tier-1 (wrong provider)
a.pane_text = mock_pane_text("(coder) some-model")
check("(coder) some-model not ok for tier-1", a.builder_model_ok(None, "free", "tier-1") == (False, "coder/some-model"))

# Test the thinking twin is ok for its own node and wrong for another
a.pane_text = mock_pane_text("(gw4) think-josh-g14")
check("(gw4) think-josh-g14 ok for tier-4", a.builder_model_ok(None, "free", "tier-4") == (True, ""))
check("(gw4) think-josh-g14 not ok for tier-3", a.builder_model_ok(None, "free", "tier-3") == (False, "gw4/think-josh-g14"))

# Test no footer lines not ok for tier-1
a.pane_text = mock_pane_text("\n\n\n")
check("no footer lines not ok for tier-1", a.builder_model_ok(None, "free", "tier-1") == (False, "unknown"))

# Test footer with multiple lines, only last non-blank counts
a.pane_text = mock_pane_text("(gw1) node-trashcan\n\n\n")
check("(gw1) node-trashcan ok for tier-1 (last non-blank)", a.builder_model_ok(None, "free", "tier-1") == (True, ""))

# Test tier-1 with wrong model shows wrong model
a.pane_text = mock_pane_text("(coder) wrong-model")
check("tier-1 with wrong model shows wrong model", a.builder_model_ok(None, "free", "tier-1") == (False, "coder/wrong-model"))

# Test tier-2 with wrong model shows wrong model
a.pane_text = mock_pane_text("(openrouter) moonshotai/kimi-k2.7-code")
check("tier-2 with wrong model shows wrong model", a.builder_model_ok(None, "free", "tier-2") == (False, "openrouter/moonshotai/kimi-k2.7-code"))

# Test tier-0 always ok (not tier-1 or tier-2)
a.pane_text = mock_pane_text("(coder) some-model")
check("tier-0 always ok", a.builder_model_ok(None, "free", "tier-0") == (True, ""))

# Test tier-5 always ok (not tier-1 or tier-2)
check("tier-5 always ok", a.builder_model_ok(None, "free", "tier-5") == (True, ""))

# Test tier-6 always ok (not tier-1 or tier-2)
check("tier-6 always ok", a.builder_model_ok(None, "free", "tier-6") == (True, ""))

sys.exit(1 if FAILS else 0)
