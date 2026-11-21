#!/usr/bin/env python3
"""aidev_tuios.py has no builder kind literals ("semi-local", "local", "free", "billed"): builders are tier ids."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "aidev_tuios.py")

KIND = re.compile(r"""(["'])(semi-local|billed|free|local)\1""")
# Substrings of the lines that may hold such a literal: the planner choice is not a builder kind.
ALLOWED = ('planner == "local"',)


def main():
    bad = []
    in_doc = False
    for n, line in enumerate(open(SRC, encoding="utf-8").read().splitlines(), 1):
        text = line.strip()
        was_doc = in_doc
        if line.count('"""') % 2:
            in_doc = not in_doc
        if was_doc or in_doc or '"""' in line or text.startswith("#"):
            continue
        code = line.split("  #")[0]
        if not KIND.search(code):
            continue
        rest = code
        for ok in ALLOWED:
            rest = rest.replace(ok, "")
        if KIND.search(rest):
            bad.append(f"{n}: {text}")
    if bad:
        print("builder kind literals left in aidev_tuios.py:\n" + "\n".join(bad))
        return 1
    print("ok: no builder kind literals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
