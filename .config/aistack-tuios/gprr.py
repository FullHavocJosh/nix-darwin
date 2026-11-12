"""gprr: rewrite the PR body with the 9B, mark the PR ready, then watch it for failed checks and feedback."""

import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import explore
import pr_describe
import pr_status


def gh(wd, *args):
    try:
        r = subprocess.run(
            ["gh", *args],
            cwd=wd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return r.returncode, r.stdout


def _git_stat(wd, *rev):
    try:
        r = subprocess.run(
            ["git", "diff", "--stat", *rev],
            cwd=wd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout if r.returncode == 0 else ""


def describe_pr(wd, prd, ask):
    code, old = gh(wd, "pr", "view", "--json", "body", "-q", ".body")
    if code != 0:
        return False, "cannot read the PR body"
    old = old.rstrip("\n")
    stat = _git_stat(wd, "origin/HEAD...HEAD") or _git_stat(wd, "HEAD~1")
    body = pr_describe.describe(prd, stat, ask, fallback=old, body=old)
    if body == old:
        return False, "PR body unchanged"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(body)
        path = f.name
    try:
        code, _ = gh(wd, "pr", "edit", "--body-file", path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if code != 0:
        return False, "gh pr edit failed, old body kept"
    return True, "PR body rewritten"


def mark_ready(wd):
    code, out = gh(wd, "pr", "view", "--json", "isDraft", "-q", ".isDraft")
    if code != 0:
        return False, "cannot read the PR state"
    if out.strip().lower() != "true":
        return True, "PR already ready"
    code, _ = gh(wd, "pr", "ready")
    if code != 0:
        return False, "gh pr ready failed"
    return True, "PR marked ready"


def monitor(wd, seconds=540, poll=20):
    deadline = time.monotonic() + seconds
    while True:
        result = pr_status.collect(wd)
        if result is None:
            return 1, "cannot read the PR (gh failed)"
        code, text = result
        if code != 3 or time.monotonic() >= deadline:
            return code, text
        time.sleep(poll)


def _load_prd(plan_dir):
    if not plan_dir:
        return None
    try:
        with open(os.path.join(plan_dir, "prd.json"), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def main(argv):
    plan_dir = None
    only_monitor = False
    no_monitor = False
    seconds = 540
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--plan-dir" and args:
            plan_dir = args.pop(0)
        elif a == "--monitor":
            only_monitor = True
        elif a == "--no-monitor":
            no_monitor = True
        elif a == "--seconds" and args:
            try:
                seconds = int(args.pop(0))
            except ValueError:
                print("gprr: --seconds needs a number", file=sys.stderr)
                return 2
        else:
            print(f"gprr: unknown argument {a}", file=sys.stderr)
            return 2
    wd = os.getcwd()
    failed = False
    if not only_monitor:
        _ok, msg = describe_pr(wd, _load_prd(plan_dir), explore.ask)
        print(f"describe: {msg}")
        ok2, msg2 = mark_ready(wd)
        print(f"ready: {msg2}")
        failed = not ok2
        if no_monitor:
            return 1 if failed else 0
    code, text = monitor(wd, seconds)
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
