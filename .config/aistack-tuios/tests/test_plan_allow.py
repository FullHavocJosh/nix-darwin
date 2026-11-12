#!/usr/bin/env python3
"""
Test the plan pane allow entries, the ~/.ai/guard denies and the layer-claude.md rules.
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios" + ".py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = 0


def check(ok, name):
    global FAILS
    if ok:
        print("PASS: " + name)
    else:
        print("FAIL: " + name)
        FAILS += 1


with tempfile.TemporaryDirectory() as tmp:
    s = os.path.join(tmp, "s")
    b = os.path.join(tmp, "b")
    a.write_backbone_settings({'claude_settings': s, 'claude_backbone': b})
    with open(b, 'r') as f:
        data = json.load(f)

perms = data.get('permissions', {})
allow = perms.get('allow', [])
deny = perms.get('deny', [])

for entry in ["Bash(cat:*)", "Bash(ls:*)", "Bash(wc:*)", "Bash(head:*)", "Bash(tail:*)", "Bash(rg:*)", "Bash(fd:*)",
              "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)",
              "Bash(tuios list-windows:*)", "Bash(tuios peek-prompt:*)", "Read(~/ai-info/**)",
              "Bash(mkdir -p ~/.ai/**)", "Bash(touch ~/.ai/**)", "Edit(~/.ai/**)", "Write(~/.ai/**)",
              "Bash(gpa --auto:*)", "Bash(gprr:*)"]:
    check(entry in allow, "allow has " + entry)

check(os.path.expanduser("~/ai-info") in perms.get('additionalDirectories', []), "additionalDirectories has ~/ai-info")

for entry in ["Bash(git commit:*)", "Bash(git push:*)", "Bash(gh:*)"]:
    check(entry not in allow, "allow lacks " + entry)
check(not any(e.startswith("Bash(gpa") and e != "Bash(gpa --auto:*)" for e in allow), "allow has no other gpa rule")
for prefix in ["Bash(rm", "Bash(mv"]:
    check(not any(e.startswith(prefix) for e in allow), "allow has no entry starting with " + prefix)

for entry in ["Edit(~/.ai/guard/**)", "Write(~/.ai/guard/**)", "Bash(mkdir -p ~/.ai/guard/**)",
              "Bash(touch ~/.ai/guard/**)"]:
    check(entry in deny, "deny has " + entry)

pre = data.get('hooks', {}).get('PreToolUse', [])
check(any(h.get('matcher') == 'Bash' for h in pre), "Bash PreToolUse hook present")

with open(os.path.join(HERE, "..", "layer-claude" + ".md"), 'r') as f:
    layer = f.read()
for rule in ["literal path, never through P= or A= variables", "Write or Edit under ~/.ai, never shell heredocs"]:
    check(rule in layer, "layer-claude.md has: " + rule)

sys.exit(1 if FAILS else 0)
