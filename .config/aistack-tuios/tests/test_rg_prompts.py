#!/usr/bin/env python3

import sys

# Read layer-build.md and check for rg -n and not grep -n
with open('.config/aistack-tuios/layer-build.md', 'r') as f:
    layer_build_content = f.read()

# Read layer-claude.md and check for fd and rg --files
with open('.config/aistack-tuios/layer-claude.md', 'r') as f:
    layer_claude_content = f.read()

FAILS = 0

# Check layer-build.md
if 'rg -n' not in layer_build_content:
    print("FAIL: layer-build.md does not contain 'rg -n'")
    FAILS += 1
else:
    print("PASS: layer-build.md contains 'rg -n'")

if 'grep -n' in layer_build_content:
    print("FAIL: layer-build.md still contains 'grep -n'")
    FAILS += 1
else:
    print("PASS: layer-build.md does not contain 'grep -n'")

# Check layer-claude.md
if 'fd' not in layer_claude_content:
    print("FAIL: layer-claude.md does not contain 'fd'")
    FAILS += 1
else:
    print("PASS: layer-claude.md contains 'fd'")

if 'rg --files' not in layer_claude_content:
    print("FAIL: layer-claude.md does not contain 'rg --files'")
    FAILS += 1
else:
    print("PASS: layer-claude.md contains 'rg --files'")

sys.exit(1 if FAILS else 0)