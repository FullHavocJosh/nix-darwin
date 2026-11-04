#!/usr/bin/env python3
"""Test the pr-status helper: exit codes pass through, pending polls, the deadline, a missing PR and the event."""

import contextlib
import importlib.util
import io
import os
import sys
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


def pr_status(data, argv, results, events):
    """cmd_pr_status with pr_status.collect returning `results` in turn (the last repeats). Returns (code, printed, polls)."""
    polls = []

    def fake_collect(wd):
        polls.append(wd)
        return results[min(len(polls) - 1, len(results) - 1)]

    a.pr_status.collect = fake_collect
    run = types.SimpleNamespace(data=data, save=lambda: None, event=lambda kind, **kw: events.append((kind, kw)))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = a.cmd_pr_status(run, argv)
    return code, out.getvalue(), polls


def main():
    real_collect, real_poll = a.pr_status.collect, a.PR_POLL_S
    a.PR_POLL_S = 0
    events = []
    wd = {"work_dir": "/wd"}
    try:
        check("pr-status is a helper", a.HELPERS.get("pr-status") is a.cmd_pr_status)

        code, out, polls = pr_status({}, [], [(0, "x")], events)
        check("no work dir refuses", code == 1 and not polls and "no work dir" in out, f"code {code}: {out}")

        code, out, polls = pr_status(wd, [], [(3, "pending"), (3, "pending"), (0, "all green")], events)
        check("pending then green returns 0", code == 0 and len(polls) == 3 and "all green" in out, f"code {code}: {out}")
        check("polls use the work dir", polls == ["/wd"] * 3, str(polls))
        check("pr_status event recorded", ("pr_status", {"code": 0}) in events, str(events))

        code, out, _ = pr_status(wd, [], [(1, "check failed")], events)
        check("code 1 passes through", code == 1 and "check failed" in out, f"code {code}: {out}")

        code, out, _ = pr_status(wd, [], [(2, "bot comment")], events)
        check("code 2 passes through", code == 2 and "bot comment" in out, f"code {code}: {out}")

        code, out, polls = pr_status(wd, [], [None], events)
        check("None means gh could not read the PR", code == 1 and "gh could not read the PR" in out and len(polls) == 1,
              f"code {code}: {out}")

        code, out, _ = pr_status(wd, ["0"], [(3, "pending")], events)
        check("deadline returns 3", code == 3 and "pending" in out and "still pending after 0 s" in out,
              f"code {code}: {out}")

        code, out, _ = pr_status(wd, ["abc"], [(0, "x")], events)
        check("bad seconds is a usage error", code == 2 and "usage" in out, f"code {code}: {out}")
    finally:
        a.pr_status.collect, a.PR_POLL_S = real_collect, real_poll
    print(f"{len(FAILS)} failed" if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
