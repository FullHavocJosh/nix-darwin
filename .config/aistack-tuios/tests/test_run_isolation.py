"""Tests that concurrent aidev runs of one project stay apart: each run keeps its plan dir and its worktree record
(project.json) under runs/<id>/, aidev_lib sees that run's, finish archives both, and runs started before per-run plan
dirs keep the shared one. Needs no tuios daemon, no model and no network. Uses this checkout's aidev_lib.py.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_run_isolation.py
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
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
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_WORKTREE_MODE"] = "none"
    os.environ["AISTACK_WORKTREE_MODE"] = "none"  # ensure_workdir never creates a worktree here
    os.environ["AISTACK_DIR"] = os.path.realpath(os.path.join(ROOT, "..", "aistack"))
    a = load("aidev_tuios", os.path.join(ROOT, "aidev_tuios.py"))
    p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))

    print("per-run plan dir and worktree record")
    rA = a.Run(p, "20260101-000001")
    rB = a.Run(p, "20260101-000002")
    check("two runs have different plan dirs", rA.plan_dir != rB.plan_dir, (rA.plan_dir, rB.plan_dir))
    check("the plan dir is runs/<id>/plan", rA.plan_dir == os.path.join(rA.dir, "plan"), rA.plan_dir)
    check("the worktree record is in the run dir", os.path.dirname(rA.meta_path) == rA.dir, rA.meta_path)
    check("two runs have different worktree records", rA.meta_path != rB.meta_path)

    print("legacy run")
    rL = a.Run(p, "20260101-000003")
    rL.data.pop("plan_dir")
    rL.save()
    got = a.Run(p, "20260101-000003").plan_dir
    check("a run without plan_dir keeps the shared plan dir", got == os.path.join(rA.state, "plan"), got)

    print("aidev_lib sees the run's paths")
    m = a.load_lib(p, rA)
    check("aidev_lib's plan dir is the run's", m.plan_dir(p) == rA.plan_dir, m.plan_dir(p))
    check("aidev_lib's worktree record is the run's", m.meta_path(p) == rA.meta_path, m.meta_path(p))
    got = a.load_lib(p).plan_dir(p)
    check("without a run aidev_lib uses the shared plan dir", got == os.path.join(rA.state, "plan"), got)

    print("worktree record per run")
    x = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-wt-"))
    a.wj(rA.meta_path, {"work_dir": x})
    got = a.load_lib(p, rA).ensure_workdir(p, {"name": "n"})[0]
    check("run A reuses its own work dir", got == x, got)
    got = a.load_lib(p, rB).ensure_workdir(p, {"name": "n"})[0]
    check("run B does not reuse run A's work dir", got == p, got)

    print("finish_work")
    a.window_named = lambda s, n: None
    os.makedirs(rA.plan_dir)
    with open(os.path.join(rA.plan_dir, "marker.txt"), "w") as fh:
        fh.write("m\n")
    a.finish_work(rA)
    check("the worktree record is removed", not os.path.exists(rA.meta_path))
    check("the plan dir is empty again", os.listdir(rA.plan_dir) == [], os.listdir(rA.plan_dir))
    done = [d for d in os.listdir(rA.dir) if d.startswith("plan-done-")]
    check("a plan-done dir holds the old plan",
          any(os.path.isfile(os.path.join(rA.dir, d, "marker.txt")) for d in done), done)
    fin = rA.data.get("finished", [{}])[-1]
    check("finished keeps the worktree record", fin.get("project", {}).get("work_dir") == x, fin)

    print("legacy finish")
    shared = os.path.join(rA.state, "plan")
    os.makedirs(shared, exist_ok=True)
    keep = os.path.join(shared, "keep.txt")
    with open(keep, "w") as fh:
        fh.write("k\n")
    a.finish_work(a.Run(p, "20260101-000003"))
    check("the shared plan dir is not archived", os.path.isfile(keep))

    print("builder permissions")
    deny = a.builder_permissions(None, state_dir="/tmp/s")["deny"]
    check("edits to every run's plan dir are denied", "Edit(//tmp/s/runs/*/plan/**)" in deny, deny)

    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
