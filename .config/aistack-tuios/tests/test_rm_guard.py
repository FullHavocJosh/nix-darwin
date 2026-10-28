#!/usr/bin/env python3
"""Test the rm guard that write_git_guard puts next to the git guard for the builder panes."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def scratch(tmp, name):
    d = os.path.join(tmp, name)
    os.makedirs(d)
    with open(os.path.join(d, "keep.txt"), "w") as f:
        f.write("keep\n")
    return d


def touch(path):
    with open(path, "w") as f:
        f.write("x\n")
    return path


def rm(shim, *args):
    return subprocess.run([shim, *args], capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        run = types.SimpleNamespace(dir=tmp)
        a.write_git_guard(run)
        shim = os.path.join(tmp, "bin", "guard", "rm")
        check("shim is executable", os.access(shim, os.X_OK))

        for i, flags in enumerate([["-rf"], ["-r"], ["-R"], ["-fr"], ["-vr"], ["--recursive"]]):
            d = scratch(tmp, f"case{i}")
            r = rm(shim, *flags, d)
            label = " ".join(flags)
            check(f"{label} exits non-zero", r.returncode != 0, f"exit {r.returncode}")
            check(f"{label} says blocked", "blocked" in r.stderr, r.stderr.strip())
            check(f"{label} leaves the directory", os.path.isfile(os.path.join(d, "keep.txt")))

        d = scratch(tmp, "single")
        f = touch(os.path.join(d, "a.txt"))
        r = rm(shim, "-f", f)
        check("-f file exits 0", r.returncode == 0, r.stderr.strip())
        check("-f file is gone", not os.path.exists(f))

        f = touch(os.path.join(d, "b.txt"))
        r = rm(shim, f)
        check("plain file exits 0", r.returncode == 0, r.stderr.strip())
        check("plain file is gone", not os.path.exists(f))

        f = touch(os.path.join(d, "-r"))
        r = rm(shim, "--", f)
        check("-- file named -r exits 0", r.returncode == 0, r.stderr.strip())
        check("-- file named -r is gone", not os.path.exists(f))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
