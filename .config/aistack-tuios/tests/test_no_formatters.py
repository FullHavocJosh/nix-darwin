#!/usr/bin/env python3
"""Test the builder pane's formatter kill switch: every formatter disabled, other keys kept, idempotent."""

import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def read(path):
    with open(path) as f:
        return f.read()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "opencode.json")
        with open(path, "w") as f:
            json.dump({"keep": 1}, f)
        got = a.no_formatters(tmp)
        check("returns the pane's config", got == path, got)
        data = json.loads(read(path))
        check("ruff disabled", data["formatter"]["ruff"] == {"disabled": True}, data["formatter"].get("ruff"))
        check("prettier disabled", data["formatter"]["prettier"] == {"disabled": True},
              data["formatter"].get("prettier"))
        check("other keys survive", data.get("keep") == 1, data)

        first = read(path)
        a.no_formatters(tmp)
        check("second call gives the same file", read(path) == first)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
