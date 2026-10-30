"""Test cmd_explore: passes question, files, root and fallback to explore.py and prints the answer."""

import contextlib
import importlib.util
import io
import os
import sys
import types

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


calls = []


def fake_explore(q, files, root, fallback):
    calls.append((q, files, root, fallback))
    return "ans"


def bad_explore(q, files, root, fallback):
    raise RuntimeError("x")


a.zen_model = lambda project: None
run = types.SimpleNamespace(
    data={"work_dir": "/w"}, project="/p", event=lambda *args, **kw: None
)

a.load_explore = lambda: types.SimpleNamespace(explore=fake_explore)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = a.cmd_explore(run, ["q", "f.txt"])
check("explore returns 0", rc == 0, rc)
check("answer printed", "ans" in buf.getvalue(), buf.getvalue())
check("question passed", calls and calls[0][0] == "q")
check("files passed", calls and calls[0][1] == ["f.txt"], calls)
check("root is work_dir", calls and calls[0][2] == "/w", calls)
check("no fallback without free model", calls and calls[0][3] is None, calls)

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = a.cmd_explore(run, [])
check("no question returns 2", rc == 2, rc)

a.load_explore = lambda: types.SimpleNamespace(explore=bad_explore)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = a.cmd_explore(run, ["q"])
check("RuntimeError returns 1", rc == 1, rc)
check("error printed", "explore: x" in buf.getvalue(), buf.getvalue())

check("explore registered", "explore" in a.HELPERS)

sys.exit(1 if FAILS else 0)
