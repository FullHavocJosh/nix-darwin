"""Tests that worktree retires a saved work dir that is gone or whose PR is merged, and still reuses one whose PR is
open. Needs no tuios daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_worktree_stale.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios


def main():
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_DIR"] = os.path.realpath(os.path.join(ROOT, "..", "aistack"))
    a = load("aidev_tuios", os.path.join(ROOT, "aidev_tuios.py"))

    recorded = []
    a.tuios = lambda *args, **k: recorded.append(args) or (0, "", "")
    a.window_named = lambda *x: None
    a.load_lib = lambda *x, **k: types.SimpleNamespace(
        load_plan=lambda p: ({}, {}, ""), validate=lambda p, v: [],
        ensure_workdir=lambda p, prd, v: ("/new-wd", True, None))

    def make_run(data):
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))
        return types.SimpleNamespace(project=tmp, session="s", meta_path=os.path.join(tmp, "meta"), data=data,
                                     event=lambda *x, **k: None, save=lambda: None)

    print("(a) a gone work dir is retired and a new one made")
    a.pr_state = lambda *x: "OPEN"
    run = make_run({"work_dir": "/gone-dir"})
    with open(run.meta_path, "w") as fh:
        json.dump({"work_dir": "/gone-dir", "pr_number": 7}, fh)
    rc = a.cmd_worktree(run, [])
    check("returns 0", rc == 0, rc)
    check("work_dir is /new-wd", run.data.get("work_dir") == "/new-wd", run.data.get("work_dir"))
    check("meta file is gone", not os.path.exists(run.meta_path))
    fin = run.data.get("finished") or [{}]
    check("finished[-1] work_dir is /gone-dir", fin[-1].get("work_dir") == "/gone-dir", fin)

    print("(b) an open PR's existing work dir is reused")
    a.pr_state = lambda *x: "OPEN"
    wd = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-wd-"))
    run = make_run({"work_dir": wd})
    rc = a.cmd_worktree(run, [])
    check("returns 0", rc == 0, rc)
    check("work_dir stays", run.data.get("work_dir") == wd, run.data.get("work_dir"))

    print("(c) a merged PR's work dir is retired")
    a.pr_state = lambda *x: "MERGED"
    run = make_run({"work_dir": wd})
    rc = a.cmd_worktree(run, [])
    check("returns 0", rc == 0, rc)
    check("work_dir is /new-wd", run.data.get("work_dir") == "/new-wd", run.data.get("work_dir"))

    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS)))
    return 1 if FAILS else 0


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FAILS = []

if __name__ == "__main__":
    sys.exit(main())
