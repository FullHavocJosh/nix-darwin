"""Test explore.py orchestration: explore and grep_context."""

import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "explore", os.path.join(HERE, "..", "explore.py")
)
explore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(explore)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


seen = []


def fake_ask(prompt, system="", max_tokens=700):
    seen.append(prompt)
    return "x" * 5000


with tempfile.TemporaryDirectory() as root:
    with open(os.path.join(root, "a.txt"), "w") as f:
        f.write("alpha\nbeta\n")

    explore.ctx_tokens = lambda: 32000
    explore.ask = fake_ask
    out = explore.explore("what is alpha", ["a.txt"], root)
    check("answer capped at 1500", len(out) == 1500, str(len(out)))
    check("prompt holds numbered lines", "1: alpha" in seen[0], seen[0])

    explore.ctx_tokens = lambda: 0
    out = explore.explore("q", ["a.txt"], root, fallback=lambda p: "fb:" + p)
    check("ctx 0 uses fallback", out.startswith("fb:q"), out)
    try:
        explore.explore("q", ["a.txt"], root)
        check("ctx 0 without fallback raises", False)
    except RuntimeError:
        check("ctx 0 without fallback raises", True)

    def run(*a):
        subprocess.run(["git", "-C", root, *a], check=True, capture_output=True)

    with open(os.path.join(root, "code.py"), "w") as f:
        f.write("def frobnicate():\n    pass\n")
    run("init", "-q")
    run("add", "code.py")
    hits = explore.grep_context(root, "where is frobnicate defined")
    check("grep_context finds word", "code.py:1:" in hits, hits)

sys.exit(1 if FAILS else 0)
