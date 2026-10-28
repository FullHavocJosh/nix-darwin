#!/usr/bin/env python3
"""Test the commit helper (its refusals, the gpa command it runs, the message, failure output and the event) and that
finish says whether the work is committed."""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []
PRD = {"title": "Plan title", "description": "Plan description.",
       "userStories": [{"id": "T1"}, {"id": "T2"}]}


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def fake_run(tmp, data, events):
    return types.SimpleNamespace(data=data, plan_dir=tmp, save=lambda: None,
                                 event=lambda kind, **kw: events.append((kind, kw)))


def commit(tmp, data, argv, status, stdout, events):
    """cmd_commit with git status `status` and gpa printing `stdout`. Returns (code, printed, subprocess calls)."""
    calls = []

    def fake_subprocess_run(cmd, **kw):
        calls.append((cmd, kw))
        return types.SimpleNamespace(returncode=0 if '"ok": true' in stdout else 1, stdout=stdout, stderr="")

    a.git_out = lambda _wd, *_args: status
    a.subprocess.run = fake_subprocess_run
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = a.cmd_commit(fake_run(tmp, data, events), argv)
    return code, out.getvalue(), calls


def main():
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "prd.json"), "w") as f:
        json.dump(PRD, f)
    real_git_out, real_run = a.git_out, a.subprocess.run
    real_finish_work, real_window_named = a.finish_work, a.window_named
    verified = {"T1": {"status": "verified"}, "T2": {"status": "verified"}}
    ok = json.dumps({"ok": True, "commit": "abc123", "branch": "b", "pushed": True})
    events = []
    try:
        code, _, calls = commit(tmp, {}, [], " M x", ok, events)
        check("no work dir refuses", code == 1 and not calls, f"code {code}")

        data = {"work_dir": "/wd", "tasks": {"T1": {"status": "verified"}, "T2": {"status": "sent"}}}
        code, out, calls = commit(tmp, data, [], " M x", ok, events)
        check("unverified task refuses", code == 1 and not calls and "T2" in out, f"code {code}: {out}")

        code, out, calls = commit(tmp, {"work_dir": "/wd", "tasks": verified}, [], "", ok, events)
        check("clean tree refuses", code == 1 and not calls, f"code {code}: {out}")

        code, out, calls = commit(tmp, {"work_dir": "/wd", "tasks": verified}, [], " M x", "log\n" + ok, events)
        check("ok gpa returns 0", code == 0 and "abc123" in out, f"code {code}: {out}")
        check("gpa called once", len(calls) == 1, str(calls))
        if calls:
            cmd, kw = calls[0]
            check("cwd is the work dir", kw.get("cwd") == "/wd", str(kw.get("cwd")))
            check("argv[0] is zsh", cmd[0] == "zsh", str(cmd))
            line = " ".join(cmd)
            check("command runs gpa --auto --json", "gpa --auto" in line and "--json" in line, line)
            check("command never waives", "--no-review" not in line and "--waive" not in line, line)
            env = kw.get("env") or {}
            check("subject defaults to the prd title", env.get("AIDEV_COMMIT_SUBJECT") == PRD["title"], str(env))
            check("body defaults to the prd description",
                  env.get("AIDEV_COMMIT_BODY") == PRD["description"], str(env.get("AIDEV_COMMIT_BODY")))
            check("env skips nix-darwin set-environment",
                  env.get("__NIX_DARWIN_SET_ENVIRONMENT_DONE") == "1", str(env.get("__NIX_DARWIN_SET_ENVIRONMENT_DONE")))

        code, _, calls = commit(tmp, {"work_dir": "/wd", "tasks": verified}, ["Subj", "Body."], " M x", ok, events)
        env = calls[0][1].get("env") if calls else {}
        check("argv overrides the prd", code == 0 and env.get("AIDEV_COMMIT_SUBJECT") == "Subj"
              and env.get("AIDEV_COMMIT_BODY") == "Body.", str(env))

        failed = json.dumps({"ok": False, "output_tail": "lint failed"})
        code, out, _ = commit(tmp, {"work_dir": "/wd", "tasks": verified}, [], " M x", failed, events)
        check("failed gpa returns 1 and prints the tail", code == 1 and "lint failed" in out, f"code {code}: {out}")

        check("commit event recorded", any(k == "commit" for k, _ in events), str(events))

        a.subprocess.run = real_run
        a.finish_work = lambda _run: "/wd"
        a.window_named = lambda _s, _n: None
        for status, want, name in ((" M x", "uncommitted", "dirty"), ("", "is committed", "clean")):
            a.git_out = lambda _wd, *_args, s=status: s
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                a.cmd_finish(types.SimpleNamespace(data={"work_dir": "/wd"}, session="s"), [])
            text = out.getvalue()
            check(f"finish on a {name} tree says {want}",
                  want in text and (name == "dirty" or "uncommitted" not in text), text)
    finally:
        a.git_out, a.subprocess.run = real_git_out, real_run
        a.finish_work, a.window_named = real_finish_work, real_window_named
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{len(FAILS)} failed" if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
