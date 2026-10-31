"""Test review_diff.py: criteria parameter in review function."""

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
    with open(os.path.join(d, "long.txt"), "w") as f:
        f.write("x" * 20000)

    recorded_systems = []

    def ask(prompt, system):
        recorded_systems.append(system)
        return "no findings"

    # Test criteria parameter
    review_diff.review(d, None, ask, criteria="must add three")
    check(
        "criteria in system",
        "must add three" in recorded_systems[0],
        recorded_systems[0],
    )

    # Test default system
    recorded_systems = []
    review_diff.review(d, None, ask, criteria="")
    check(
        "default system equals SYSTEM",
        recorded_systems[0] == review_diff.SYSTEM,
        recorded_systems[0],
    )

    # Test diff truncation
    cut = review_diff.file_diff(d, "long.txt", max_chars=1000)
    full = review_diff.file_diff(d, "long.txt", max_chars=100000)
    check("diff truncation marker", cut.endswith("[diff truncated]"), cut[-20:])
    check("diff truncation content", cut[:1000] == full[:1000])

sys.exit(1 if FAILS else 0)
