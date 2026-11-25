"""Test that Run.save drops tasks this instance deleted and finish_work keeps followups.txt."""

import copy
import importlib.util
import json
import os
import sys
import tempfile
import types

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


# (a) Run.save drops a task this instance deleted, keeps one another helper added
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "state" + ".json")
    with open(path, "w") as fh:
        json.dump({"tasks": {"T1": {"status": "verified"}}}, fh)
    r = a.Run.__new__(a.Run)
    r.dir = tmp
    r.path = path
    r.data = a.rj(r.path)
    r._base = copy.deepcopy(r.data)
    with open(path, "w") as fh:
        json.dump(
            {"tasks": {"T1": {"status": "verified"}, "T2": {"status": "pending"}}}, fh
        )
    r.data["tasks"] = {}
    r.save()
    disk = a.rj(path) or {}
    tasks = disk.get("tasks") or {}
    check("save drops deleted T1", "T1" not in tasks, str(tasks))
    check("save keeps T2 from another helper", "T2" in tasks, str(tasks))

# (b) finish_work archives the plan dir and carries followups.txt over
with tempfile.TemporaryDirectory() as tmp:
    plan = os.path.join(tmp, "plan")
    os.makedirs(plan)
    with open(os.path.join(plan, "followups.txt"), "w") as fh:
        fh.write("fix x\n")
    with open(os.path.join(plan, "prd.md"), "w") as fh:
        fh.write("prd\n")
    run = types.SimpleNamespace(
        data={"plan_dir": plan, "tasks": {"T1": {}}},
        plan_dir=plan,
        dir=tmp,
        project=tmp,
        session="s",
        meta_path=os.path.join(tmp, "meta"),
        event=lambda *x, **k: None,
        save=lambda: None,
    )
    a.window_named = lambda *x, **k: None
    a.finish_work(run)
    fu = os.path.join(plan, "followups.txt")
    text = ""
    if os.path.isfile(fu):
        with open(fu) as fh:
            text = fh.read()
    check("followups.txt carried over", "fix x" in text, repr(text))
    check("prd gone from plan", not os.path.exists(os.path.join(plan, "prd.md")))
    done = [d for d in os.listdir(tmp) if d.startswith("plan-done-")]
    check(
        "plan-done dir holds prd",
        any(os.path.isfile(os.path.join(tmp, d, "prd.md")) for d in done),
        str(done),
    )
    check("tasks cleared", run.data.get("tasks") == {}, str(run.data.get("tasks")))

sys.exit(1 if FAILS else 0)
