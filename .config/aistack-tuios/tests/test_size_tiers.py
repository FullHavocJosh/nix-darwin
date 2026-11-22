"""Tests for size_problems scaling by tier ctx (aidev_tuios.py). Needs no tuios daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_size_tiers.py
"""
import importlib.util
import os
import sys
import tempfile

os.environ["AISTACK_ZEN_KEY"] = "1"
os.environ["AIDEV_SEMI_LOCAL"] = "off"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.environ["AISTACK_DIR"] = os.path.join(os.path.dirname(ROOT), "aistack")
os.environ["AIDEV_TIERS_FILE"] = os.path.join(tempfile.mkdtemp(prefix="aidev-test-tiers-"), "none.json")
os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
for var in ("AIDEV_TUIOS_TASK_MAX_CHARS", "AIDEV_TUIOS_TASK_MAX_READ"):
    os.environ.pop(var, None)
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    sys.path.insert(0, ROOT)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def story(desc, **extra):
    return {"userStories": [dict({"id": "T1", "title": "t", "description": desc, "acceptanceCriteria": ["ok"]}, **extra)]}


def main():
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))
    a.tiers = lambda: {"tier-0": {"ctx": 32768, "enabled": True}, "tier-1": {"ctx": 16384, "enabled": True},
                       "tier-2": {"ctx": 65536, "enabled": True}}
    a.tier_online = lambda tid, run=None: False
    big = "x" * 4000
    check("4000 characters pass at ctx 65536", a.size_problems(story(big), ctx=65536) == [])
    over = a.size_problems(story(big), ctx=16384)
    check("4000 characters fail at ctx 16384", len(over) == 1 and "characters" in over[0] and "16384" in over[0], over)
    check("default ctx is tier-1 when no tier is online", a.default_target_ctx() == 16384, a.default_target_ctx())
    check("default ctx fails 4000 characters", len(a.size_problems(story(big))) == 1)
    a.tier_online = lambda tid, run=None: tid == "tier-2"
    check("default ctx is the online tier", a.default_target_ctx() == 65536)
    check("default ctx is the smallest online ctx", a.default_target_ctx() == 65536)
    a.tier_online = lambda tid, run=None: False
    check("default ctx is the smallest enabled ctx when none is online", a.default_target_ctx() == 16384)
    pinned = a.size_problems(story(big, tier=2), ctx=16384)
    check("a story tier 2 uses the tier-2 ctx", pinned == [], pinned)
    pinned = a.size_problems(story(big, tier=1), ctx=65536)
    check("a story tier 1 uses the tier-1 ctx", len(pinned) == 1 and "16384" in pinned[0], pinned)
    a.tiers = lambda: {"tier-0": {"ctx": 32768, "enabled": True}, "tier-1": {"ctx": 16384, "enabled": False},
                       "tier-2": {"ctx": 0, "enabled": False}}
    check("default ctx is tier-0 when tiers 1 and 2 are disabled", a.default_target_ctx() == 32768)
    pinned = a.size_problems(story(big, tier=1), ctx=65536)
    check("a disabled tier does not pin the ctx", pinned == [], pinned)
    a.tiers = lambda: __import__("aidev_tiers").load_tiers()
    os.environ["AIDEV_TUIOS_TASK_MAX_CHARS"] = "100"
    try:
        env = a.size_problems(story("x" * 150), ctx=65536)
        check("env AIDEV_TUIOS_TASK_MAX_CHARS wins", len(env) == 1 and "over 100" in env[0], env)
    finally:
        del os.environ["AIDEV_TUIOS_TASK_MAX_CHARS"]
    root = tempfile.mkdtemp(prefix="aidev-test-read-")
    with open(os.path.join(root, "a.py"), "w") as fh:
        fh.write("x" * 50000)
    os.environ["AIDEV_TUIOS_TASK_MAX_READ"] = "1000"
    try:
        env = a.size_problems(story("change a.py to add a counter"), root, ctx=65536)
        check("env AIDEV_TUIOS_TASK_MAX_READ wins", len(env) == 1 and "over 1000" in env[0], env)
    finally:
        del os.environ["AIDEV_TUIOS_TASK_MAX_READ"]
    many = "edit a.py b.py c.py d.py"
    for ctx in (65536, 16384):
        res = a.size_problems(story(many), ctx=ctx)
        check(f"4 files fail at ctx {ctx}", len(res) == 1 and "files" in res[0], res)
    if FAILS:
        print(f"{len(FAILS)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
