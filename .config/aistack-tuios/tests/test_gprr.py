"""Test gprr: describe writes or keeps the body, mark_ready skips non-drafts, monitor returns the status code."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gprr", os.path.join(HERE, "..", "gprr.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

FAILS = []
GOOD = "## Summary\nShort.\n\n## Changes\n- Did it"


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def raising(_text, _system):
    raise RuntimeError("down")


def fake(calls, draft="true", body="old body"):
    def gh(_wd, *args):
        calls.append(args)
        if args[:2] == ("pr", "view") and "body" in args:
            return 0, body + "\n"
        if args[:2] == ("pr", "view") and "isDraft" in args:
            return 0, draft + "\n"
        if args[:2] == ("pr", "edit"):
            with open(args[args.index("--body-file") + 1], encoding="utf-8") as f:
                calls.append(("written", f.read()))
        return 0, ""

    return gh


def main():
    calls = []
    g.gh = fake(calls)
    ok, _ = g.describe_pr(".", None, lambda _t, _s: GOOD)
    written = [c[1] for c in calls if c[0] == "written"]
    check("describe_pr edits the body", ok and written == [GOOD], str(calls))

    calls.clear()
    ok, _ = g.describe_pr(".", None, raising)
    check("describe_pr keeps the old body when ask raises", not ok and not any(c[:2] == ("pr", "edit") for c in calls), str(calls))

    calls.clear()
    g.gh = fake(calls, draft="false")
    ok, _ = g.mark_ready(".")
    check("mark_ready skips a ready PR", ok and ("pr", "ready") not in calls, str(calls))

    calls.clear()
    g.gh = fake(calls, draft="true")
    ok, _ = g.mark_ready(".")
    check("mark_ready readies a draft", ok and ("pr", "ready") in calls, str(calls))

    g.pr_status.collect = lambda _wd: (2, "OPEN FEEDBACK")
    check("monitor returns the status code", g.monitor(".", seconds=0, poll=0) == (2, "OPEN FEEDBACK"))
    g.pr_status.collect = lambda _wd: None
    check("monitor returns 1 when gh is unreadable", g.monitor(".", seconds=0, poll=0)[0] == 1)
    g.pr_status.collect = lambda _wd: (3, "pending")
    check("monitor returns 3 when still pending", g.monitor(".", seconds=0, poll=0)[0] == 3)
    print(f"{len(FAILS)} failed" if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
