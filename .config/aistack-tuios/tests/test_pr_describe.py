"""Test pr_describe: input building, reference wrapping and the fallbacks."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pr_describe", os.path.join(HERE, "..", "pr_describe.py"))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

FAILS = []
PRD = {
    "title": "Plan title",
    "description": "Plan description.",
    "userStories": [
        {"id": "T1", "title": "First story", "acceptanceCriteria": ["crit one"]},
        {"id": "T2", "title": "Second story", "acceptanceCriteria": ["crit two"]},
    ],
}
STAT = " a.py | 2 +-"
GOOD = "## Summary\nFixes #5 and `#6`.\n\n## Changes\n- Did it"


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def raising(_text, _system):
    raise RuntimeError("down")


def main():
    text = p.build_input(PRD, STAT)
    check("input names the stories", "First story" in text and "Second story" in text and "crit two" in text, text)
    check("input has the plan and the stat", "Plan title" in text and STAT in text, text)
    text = p.build_input(None, STAT, "old body")
    check("input uses the body without a plan", "old body" in text and STAT in text, text)

    out = p.clean(GOOD, "fb")
    check("clean wraps bare refs only", "Fixes `#5` and `#6`." in out and "``" not in out, out)
    check("clean falls back on an empty reply", p.clean("  ", "fb") == "fb")
    check("clean falls back without a summary", p.clean("just text", "fb") == "fb")

    seen = []

    def ask(text, system):
        seen.append((text, system))
        return GOOD

    out = p.describe(PRD, STAT, ask, "fb")
    check("describe returns the cleaned reply", "`#5`" in out, out)
    check("describe passes input and system", seen and seen[0][1] == p.SYSTEM and "First story" in seen[0][0])
    check("describe falls back when ask raises", p.describe(PRD, STAT, raising, "fb") == "fb")
    check("describe falls back on an empty reply", p.describe(PRD, STAT, lambda _t, _s: "", "fb") == "fb")
    print(f"{len(FAILS)} failed" if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
