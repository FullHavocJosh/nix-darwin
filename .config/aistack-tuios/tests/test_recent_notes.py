"""Test that task prompts carry only the newest NOTES_KEEP notes."""

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


check("two notes kept", a.recent_notes(["a", "b"]) == ["a", "b"])
check("None gives empty list", a.recent_notes(None) == [])

five = ["n1", "n2", "n3", "n4", "n5"]
got = a.recent_notes(five)
check("five notes give 4 entries", len(got) == 4, repr(got))
check("first entry counts left-out notes", "2 earlier notes left out" in got[0], repr(got[0]))
check("newest three follow", got[1:] == ["n3", "n4", "n5"], repr(got[1:]))

prd = {"name": "p", "description": "d"}
story = {"id": "T1", "title": "t", "description": "x", "acceptanceCriteria": ["c"]}
prompt = a.task_prompt(prd, story, ["true"], ["- n1", "- n2", "- n3", "- n4", "- n5"])
check("prompt has newest note", "- n5" in prompt)
check("prompt drops oldest note", "- n1" not in prompt)

sys.exit(1 if FAILS else 0)
