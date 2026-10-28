#!/usr/bin/env python3
"""Test that write_build_pi writes the builder's pi model list and copies aidev's pi extensions."""

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(SRC, "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {"pi_build": tmp}
        model = a.write_build_pi(cfg)
        check("returns a coder/ model", isinstance(model, str) and model.startswith("coder/"), repr(model))
        check("model list exists", os.path.isfile(os.path.join(tmp, "models.json")))
        for name in a.PI_BUILD_EXTENSIONS:
            dst = os.path.join(tmp, "extensions", name)
            check(f"{name} copied", os.path.isfile(dst))
            check(f"{name} matches source", os.path.isfile(dst) and read(dst) == read(os.path.join(SRC, name)))
        try:
            a.write_build_pi(cfg)
            err = ""
        except Exception as e:
            err = str(e)
        check("second call works", not err, err)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
