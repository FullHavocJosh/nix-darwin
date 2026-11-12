"""Tests for backtick_refs and pr_title_and_body in aidev_lib.py: bare #N references get backticks, so GitHub adds no
cross-reference event to PR N's timeline.

Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_pr_refs.py
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_lib", os.path.join(HERE, "..", "aidev_lib.py"))
aidev_lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aidev_lib)

FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


br = aidev_lib.backtick_refs
for src, want in [
    ("Stacked on #90.", "Stacked on `#90`."),
    ("`#90`", "`#90`"),
    ("see `foo #90`", "see `foo #90`"),
    ("## Summary", "## Summary"),
    ("a&#123;", "a&#123;"),
    ("pull/90#12", "pull/90#12"),
    ("x#90", "x#90"),
]:
    got = br(src)
    check(f"backtick_refs({src!r}) == {want!r}", got == want, got)

_, title, body = aidev_lib.pr_title_and_body(
    {"title": "Fix #7", "description": "After #90.",
     "userStories": [{"id": "T1", "title": "Do #3", "acceptanceCriteria": ["ok #4"]}]},
    {"T1": ["echo #5"]},
)
check("title wraps #7", "`#7`" in title, title)
check("summary wraps #90", "`#90`" in body, body)
check("story title wraps #3", "`#3`" in body, body)
check("criteria wrap #4", "`#4`" in body, body)
check("verify command kept as `echo #5`", "`echo #5`" in body, body)
check("body has no Opened by trailer", "Opened by" not in body and "---" not in body, body)

if FAILS:
    print(f"{len(FAILS)} failed")
    sys.exit(1)
print("all passed")
