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

    # Test 40KB cap
    explore.ctx_tokens = lambda: 32000
    explore.ask = fake_ask
    with open(os.path.join(root, "big.txt"), "w") as f:
        f.write("\n".join("x" * 99 for _ in range(500)))  # 500 lines of 99 'x' chars each
    n = len(seen)
    result = explore.explore("q", ["big.txt"], root, fallback=lambda p: "fb")
    check("50KB file goes to fallback", result == "fb" and len(seen) == n, f"result={result}, seen_len={len(seen)}, n={n}")
    
    # Test line range functionality
    explore.ctx_tokens = lambda: 131072  # This should be large enough
    explore.ask = fake_ask
    result = explore.explore("q", ["big.txt:1-3"], root)
    check("line range uses 9B", len(seen) == n + 1 and "1: xxx" in seen[-1], f"len(seen)={len(seen)}, n={n}, last_seen={seen[-1]}")

sys.exit(1 if FAILS else 0)
