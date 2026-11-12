#!/usr/bin/env python3
"""
Test the billed builder permissions with a work dir: edits and file commands inside it, ~/.ai read-only, denies kept.
"""
import importlib.util
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
    wdir = os.path.join(tmp, ".worktrees", "w1")
    os.makedirs(wdir)
    wd = os.path.realpath(wdir)
    p = a.builder_permissions(None, '/s/st', work_dir=wdir)

allow = p['allow']
deny = p['deny']

for tool in ("Edit", "MultiEdit", "Write"):
    entry = f"{tool}(//{wd.lstrip('/')}/**)"
    check(entry in allow, "allow " + entry)

for entry in [f"Bash(mkdir -p {wd}/*)", f"Bash(touch {wd}/*)", f"Bash(mv {wd}/* {wd}/*)",
              f"Bash(cp {wd}/* {wd}/*)", f"Bash(rm {wd}/*)", f"Bash(rm -r {wd}/*)"]:
    check(entry in allow, "allow " + entry)

ai = os.path.expanduser('~/.ai').lstrip('/')
check(f"Read(//{ai}/**)" in allow, "allow Read of ~/.ai")
for tool in ("Edit", "MultiEdit", "Write"):
    check(f"{tool}(//{ai}/**)" in deny, f"deny {tool} of ~/.ai")

for path in ("//s/st/plan/**", "//s/st/runs/*/plan/**", "//s/st/runs/*/state.json", "//s/st/runs/*/events.jsonl"):
    for tool in ("Edit", "MultiEdit"):
        check(f"{tool}({path})" in deny, f"deny {tool}({path})")

for entry in ("Bash(rm -rf *)", "Bash(gh *)", "Bash(sudo *)", "Bash(git push *)", "Bash(git commit *)"):
    check(entry in deny, "deny " + entry)

writers = [e for e in allow if e.startswith(("Edit(", "MultiEdit(", "Write(", "Bash(mkdir", "Bash(touch", "Bash(mv",
                                              "Bash(cp", "Bash(rm"))]
check(bool(writers) and all(wd in e for e in writers), "write-capable allow entries stay in the work dir")

default = a.builder_permissions(None, '/s/st')
check(default == a.builder_permissions(None, '/s/st', work_dir=None), "work_dir=None equals the default")
check(not any(e.startswith("Write(") for e in default['allow'] + default['deny']), "default has no Write( entry")

sys.exit(1 if FAILS else 0)
