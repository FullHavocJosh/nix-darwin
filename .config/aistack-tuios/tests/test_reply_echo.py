"""Test that the builder reply echo is capped at REPLY_ECHO_MAX."""

import importlib.util
import inspect
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


check("REPLY_ECHO_MAX is 300", a.REPLY_ECHO_MAX == 300)

source = inspect.getsource(a.cmd_wait_task)
check("REPLY_ECHO_MAX is in cmd_wait_task source", "REPLY_ECHO_MAX" in source)
check("old [:1500] is not in cmd_wait_task source", "[:1500]" not in source)

sys.exit(1 if FAILS else 0)