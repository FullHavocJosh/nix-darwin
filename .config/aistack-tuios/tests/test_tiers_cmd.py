#!/usr/bin/env python3
"""Tests for cmd_tiers in aidev_tuios: text and --json output, offline tiers.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_tiers_cmd.py
"""
import contextlib
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(os.path.dirname(ROOT), "aistack")
os.environ["AIDEV_TIERS_FILE"] = os.path.join(HERE, "no-such-tiers.json")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cmd(mod, argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.cmd_tiers(None, argv)
    return code, buf.getvalue()


def main():
    sys.path.insert(0, ROOT)
    mod = load("aidev_tuios", os.path.join(ROOT, "aidev_tuios.py"))
    mod.tier_online = lambda tid, run=None: tid in ("tier-2", "tier-4")
    code, out = run_cmd(mod, [])
    lines = out.splitlines()
    check("text exits 0", code == 0)
    check("text has five lines", len(lines) == 5, out)
    check("tier-2 line", lines[2].startswith("tier-2 build-local-tier-2 ctx 65536 online limits chars "), lines[2])
    check("offline tier shows offline", "offline" in lines[0] and "online" not in lines[0], lines[0])
    check("tier-3 ctx n/a", "ctx n/a" in lines[3], lines[3])
    code, out = run_cmd(mod, ["--json"])
    data = json.loads(out)
    check("json has five entries", len(data) == 5)
    keys = {"id", "pane", "kind", "ctx", "online", "enabled", "max_chars", "max_read", "max_files"}
    check("json keys", all(set(d) == keys for d in data))
    check("json online flags", [d["online"] for d in data] == [False, False, True, False, True])
    need = mod.task_need({"title": "t", "description": "d", "acceptanceCriteria": []}, None)
    check("task_need counts the overhead", need >= 12000, str(need))
    mod = load("aidev_tuios2", os.path.join(ROOT, "aidev_tuios.py"))
    seen = []

    def fake_zen(run, refresh=False):
        seen.append(run.project)
        return {"state": "none", "model": None, "detail": "", "models": []}

    mod.zen_status = fake_zen
    try:
        online = mod.tier_online("tier-3")
    except Exception as e:
        online = repr(e)
    check("tier_online tier-3 without a run", online is False, str(online))
    check("tier_online passes a project", len(seen) == 1 and bool(seen[0]), str(seen))
    mod = load("aidev_tuios3", os.path.join(ROOT, "aidev_tuios.py"))
    mod.zen_status = lambda run, refresh=False: run.project.nope
    code, out = run_cmd(mod, [])
    check("cmd_tiers with a raising zen_status", code == 0 and len(out.splitlines()) == 5, out)
    for pane, want in (("build-local-tier-0", True), ("build-free-tier-3", True), ("build-billed-tier-4", True),
                       ("build-local-tier-1", False), ("build-local-tier-2", False), ("", False), (None, False)):
        check(f"keeps_builder {pane!r}", mod.keeps_builder(pane) is want)
    for pane in ("tier-0", "tier-3", "tier-4"):
        check(f"keeps_builder {pane}", mod.keeps_builder(pane) is True)
    if FAILS:
        print(f"{len(FAILS)} failed")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
