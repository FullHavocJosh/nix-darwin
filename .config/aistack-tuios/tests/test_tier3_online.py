#!/usr/bin/env python3
"""Regression test: tier_online('tier-3') with run=None must be True when a free Zen model is available (the run stub
needs data and save). No network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_tier3_online.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(os.path.dirname(ROOT), "aistack")  # this checkout's zen_models.py
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


def main():
    for var in ("AIDEV_TUIOS_SESSION", "AIDEV_TUIOS_RUN", "AIDEV_TUIOS_PROJECT", "AIDEV_TUIOS_BUILDER"):
        os.environ.pop(var, None)
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    a.zen_key_present = lambda: True
    a.repo_private = lambda project: "no"
    payload = json.dumps({"models": [{"model": "m", "state": "available"}], "best": "m"})
    a.subprocess.run = lambda *args, **kw: types.SimpleNamespace(returncode=0, stdout=payload, stderr="")

    print("tier-3 online with run=None")
    check("tier-3 is online", a.tier_online("tier-3") is True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
