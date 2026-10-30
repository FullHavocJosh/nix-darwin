"""Test cmd_review_diff: passes work dir, paths and ask to review_diff.py and prints the review."""

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


def fake_review(wd, paths, ask):
    calls.append((wd, paths, ask))
    return "### f: no findings"


a.load_review_diff = lambda: types.SimpleNamespace(review=fake_review)
a.load_explore = lambda: types.SimpleNamespace(ask=lambda p, s="": "x")
run = types.SimpleNamespace(data={"work_dir": "/w"}, event=lambda *args, **kw: None)

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = a.cmd_review_diff(run, [])
check("review-diff returns 0", rc == 0, rc)
check("review printed", "### f: no findings" in buf.getvalue(), buf.getvalue())
check("work dir passed", calls and calls[0][0] == "/w", calls)
check("no argv gives paths None", calls and calls[0][1] is None, calls)

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = a.cmd_review_diff(run, ["a.txt"])
check("paths returns 0", rc == 0, rc)
check("paths passed", len(calls) > 1 and calls[1][1] == ["a.txt"], calls)

buf = io.StringIO()
run2 = types.SimpleNamespace(data={}, event=lambda *args, **kw: None)
with contextlib.redirect_stdout(buf):
    rc = a.cmd_review_diff(run2, [])
check("no work dir returns 1", rc == 1, rc)
check("no work dir message", "no work dir" in buf.getvalue(), buf.getvalue())

check("review-diff registered", "review-diff" in a.HELPERS)

sys.exit(1 if FAILS else 0)
