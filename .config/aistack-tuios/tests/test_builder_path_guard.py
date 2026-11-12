#!/usr/bin/env python3
"""
Test the builder path guard hook: rm, mv, cp, mkdir and touch stay inside the work dir.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "..", "builder_path_guard" + ".py")

FAILS = 0


def check(ok, name):
    global FAILS
    if ok:
        print("PASS: " + name)
    else:
        print("FAIL: " + name)
        FAILS += 1


def run_guard(wd, event):
    p = subprocess.run([sys.executable, GUARD, wd], input=json.dumps(event), capture_output=True, text=True)
    return p.stdout.strip()


def bash(command):
    return {'tool_name': 'Bash', 'tool_input': {'command': command}}


def denied(out):
    if not out:
        return False
    try:
        return json.loads(out)['hookSpecificOutput']['permissionDecision'] == 'deny'
    except (ValueError, KeyError):
        return False


with tempfile.TemporaryDirectory() as tmp:
    wd = os.path.realpath(os.path.join(tmp, ".worktrees", "w1"))
    os.makedirs(wd)
    out = os.path.join(os.path.realpath(tmp), "out")
    os.makedirs(out)
    os.symlink(out, os.path.join(wd, "link"))

    for cmd in [
        f"rm {wd}/../x",
        f"rm {wd}/a /etc/passwd",
        f"mv {wd}/a /tmp/b",
        f"cp /etc/hosts {wd}/h",
        f"rm -r {wd}",
        "rm $HOME/x",
        f"rm {wd}/a && rm /etc/x",
        "touch ../x",
        f"rm {wd}/link/f",
        "mkdir -p ~/x",
        f"cp {wd}/a {wd}/b --target-directory=/etc",
        f"mv -t/etc {wd}/a",
    ]:
        check(denied(run_guard(wd, bash(cmd))), "deny: " + cmd)

    for cmd in [
        f"rm {wd}/a",
        f"rm -f {wd}/a",
        f"rm -r {wd}/sub",
        f"mv {wd}/a {wd}/b",
        f"mkdir -p {wd}/new/dir",
        f"cp {wd}/a {wd}/b",
        "touch a.txt",
        "ls /etc",
        "rg foo",
        "git status",
    ]:
        check(run_guard(wd, bash(cmd)) == "", "allow: " + cmd)

    check(run_guard(wd, {'tool_name': 'Read', 'tool_input': {'command': 'rm /etc/x'}}) == "", "non-Bash event is silent")

sys.exit(1 if FAILS else 0)
