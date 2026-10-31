"""Test review_diff.py: changed_files, file_diff and review in a tmp git repo."""

import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "review_diff", os.path.join(HERE, "..", "review_diff.py")
)
review_diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_diff)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def git(d, *args):
    subprocess.run(
        ["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
    )


with tempfile.TemporaryDirectory() as d:
    git(d, "init", "-q")
    with open(os.path.join(d, "a.txt"), "w") as f:
        f.write("one\ntwo\n")
    git(d, "add", "a.txt")
    git(d, "commit", "-q", "-m", "init")
    with open(os.path.join(d, "a.txt"), "w") as f:
        f.write("one\ntwo\nthree\n")
    with open(os.path.join(d, "b.txt"), "w") as f:
        f.write("new1\nnew2\n")

    check("changed_files", review_diff.changed_files(d) == ["a.txt", "b.txt"])
    check("file_diff tracked", "+three" in review_diff.file_diff(d, "a.txt"))
    check(
        "file_diff untracked",
        review_diff.file_diff(d, "b.txt") == "+new1\n+new2\n",
        review_diff.file_diff(d, "b.txt"),
    )
    check("file_diff cut", review_diff.file_diff(d, "a.txt", 5).endswith('[diff truncated]') and review_diff.file_diff(d, "a.txt", 5)[:5] == review_diff.file_diff(d, "a.txt", 10000)[:5])

    def ask(prompt, system):
        return "no findings" if "+three" in prompt else "line 2: bug"

    out = review_diff.review(d, None, ask)
    print(out)
    check("no findings form", "### a.txt: no findings" in out, out)
    check("findings form", "### b.txt\nline 2: bug" in out, out)
    check("stat line", "a.txt | 1 +" in out, out)

    def boom(prompt, system):
        raise RuntimeError("x")

    out = review_diff.review(d, None, boom)
    check("runtime error", "### a.txt: not reviewed (x)" in out, out)

    out = review_diff.review(d, None, ask, max_chars=10)
    check("size cap", "not reviewed (size cap): b.txt" in out, out)

sys.exit(1 if FAILS else 0)
