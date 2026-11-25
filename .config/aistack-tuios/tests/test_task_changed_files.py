"""Test that retry prompts and handoff notes cover only the task's own changed files."""

import importlib.util
import inspect
import os
import subprocess
import sys
import tempfile

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


def git(d, *args):
    # check=False: the builder panes' git guard refuses commit; with every file untracked instead,
    # scope_fingerprint hashes them all, so task_changed_files gives the same answer.
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-C", d, *args],
        check=False,
        capture_output=True,
        stdin=subprocess.DEVNULL,
    ).returncode


def write(d, name, text):
    with open(os.path.join(d, name), "w") as fh:
        fh.write(text)


with tempfile.TemporaryDirectory() as d:
    git(d, "init", "-q")
    for name in ("a.txt", "b.txt", "d.txt"):
        write(d, name, name + "\n")
    git(d, "add", "a.txt", "b.txt", "d.txt")
    if git(d, "commit", "-q", "-m", "init"):  # refused: unstage so the files read as untracked
        git(d, "rm", "-q", "--cached", "a.txt", "b.txt", "d.txt")
    write(d, "d.txt", "earlier task\n")
    t = {"scope_base": a.scope_fingerprint(d)}
    write(d, "b.txt", "this task\n")
    write(d, "c.txt", "new\n")
    got = a.task_changed_files(t, d)
    check("only this task's files", got == ["b.txt", "c.txt"], repr(got))
    check("no scope_base gives None", a.task_changed_files({}, d) is None)
    check("no work dir gives None", a.task_changed_files(t, None) is None)

check(
    "cmd_send_task uses task_changed_files",
    "task_changed_files(" in inspect.getsource(a.cmd_send_task),
)
check(
    "guard_trip uses task_changed_files",
    "task_changed_files(" in inspect.getsource(a.guard_trip),
)

sys.exit(1 if FAILS else 0)
