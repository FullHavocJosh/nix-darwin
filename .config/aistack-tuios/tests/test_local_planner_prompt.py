#!/usr/bin/env python3
"""Test layer-planner-local.md: heading, length limit and the six rules for the local 9B planner."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "..", "layer-planner-local.md")) as f:
    layer = f.read()

FAILS = []


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    if not cond:
        FAILS.append(name)


check(
    "first line is the local planner heading",
    layer.splitlines()[0] == "# aidev: local planner rules",
)
check("layer is under 1800 characters", len(layer) < 1800)
check("rule 1: says it is a small local model", "small local model" in layer)
check("rule 1: asks Lumo for every library, tool, API or version", "ask-lumo" in layer)
check("rule 1: plans from Lumo, never from memory", "never from memory" in layer)
check("rule 1: has the --none-needed waiver", "--none-needed" in layer)
check("rule 2: reads saved research notes before asking again", "research" in layer)
check("rule 3: uses explore for code questions", "explore" in layer)
check("rule 3: reads at most 60 lines at a time", "60 lines" in layer)
check("rule 3: searches with rg, never grep or find", "rg" in layer)
check("rule 4: writes one task per file", "one task per file" in layer)
check(
    "rule 4: keeps task descriptions under 2000 characters", "2000 characters" in layer
)
check("rule 5: runs check-plan after every plan edit", "check-plan" in layer)
check("rule 6: reports builder replies in two lines", "two lines" in layer)

sys.exit(1 if FAILS else 0)
