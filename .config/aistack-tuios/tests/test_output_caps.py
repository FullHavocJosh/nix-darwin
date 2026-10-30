"""Test the Lumo answer limit and pane_tail, which feeds the stall report."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def main():
    check("Lumo answers are capped at 250 words", "250 words" in a.LUMO_PREAMBLE)

    real_tuios = a.tuios
    a.tuios = lambda *args, **kw: (0, "a\n\nb\nc\nd\n", "")
    check(
        "pane_tail keeps the last 3 non-blank lines",
        a.pane_tail("s", "x") == "b\nc\nd",
        repr(a.pane_tail("s", "x")),
    )
    a.tuios = lambda *args, **kw: (1, "", "")
    check("pane_tail is empty when the capture fails", a.pane_tail("s", "x") == "")
    a.tuios = real_tuios
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
