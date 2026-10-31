#!/usr/bin/env python3
"""Test the research prompts: layer-lumo.md asks for analysis, layer-claude.md offers ask-lumo on lumo-max."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "..", "layer-lumo.md")) as f:
    lumo = f.read()
with open(os.path.join(HERE, "..", "layer-claude.md")) as f:
    claude = f.read()

FAILS = []


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    if not cond:
        FAILS.append(name)


check("layer-lumo.md asks for trade-offs", "trade-offs" in lumo)
check("layer-lumo.md keeps SEARCH-CONFIRMATION", "SEARCH-CONFIRMATION" in lumo)
check("layer-lumo.md no longer says Be concise", "Be concise" not in lumo)
check("layer-claude.md says ask-lumo runs lumo-max", "lumo-max" in claude)
check("layer-claude.md never says must use ask-lumo", "must use ask-lumo" not in claude)
check(
    "layer-claude.md never says always use ask-lumo",
    "always use ask-lumo" not in claude,
)

sys.exit(1 if FAILS else 0)
