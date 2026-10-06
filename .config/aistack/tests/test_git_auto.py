"""Tests for the AI-caller interface of gpr / gpc / gpa (--auto, --title, --description, -m, --json).
Uses a local bare repo as origin and a stub `gh`; nothing touches GitHub or an AI provider.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_git_auto.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FUNCS = os.path.join(ROOT, ".zshrc_functions_git")
FAILS = []

def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond: FAILS.append(name)

def sh(cmd, cwd, env=None, timeout=120):
    e = dict(os.environ, **(env or {}))
    for k in ("AI_LOCAL_DEFAULT", "AI_LOCAL_ONLY", "HERDR_ENV"): e.pop(k, None)
    return subprocess.run(["zsh", "-c", cmd], cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)

def git(cwd, *a): return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=test@example.com", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()

def make_world():
    t = tempfile.mkdtemp(prefix="gitauto-"); origin = t + "/origin.git"; repo = t + "/repo"; bin_ = t + "/bin"
    subprocess.run(["git", "init", "-q", "--bare", origin]); subprocess.run(["git", "clone", "-q", origin, repo], capture_output=True)
    git(repo, "checkout", "-q", "-b", "main"); open(repo + "/README.md", "w").write("hi\n")
    git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "init"); git(repo, "push", "-q", "-u", "origin", "main")
    os.makedirs(bin_)
    open(bin_ + "/gh", "w").write(f"""#!/bin/sh
# stub gh: pr view -> no PR, pr list -> none, pr create -> record the call and print a URL
case "$1 $2" in
  "pr view") exit 1 ;;
  "pr list") echo "[]" ;;
  "pr create") printf '%s\\n' "$@" > {t}/gh-create.args; echo "https://github.com/test/repo/pull/7" ;;
esac
""")
    os.chmod(bin_ + "/gh", 0o755)
    return t, repo, {"PATH": bin_ + ":" + os.environ["PATH"]}

AIFUNCS = os.path.join(ROOT, ".zshrc_functions_ai")
def functions(cmd): return f"source {FUNCS} 2>/dev/null; source {AIFUNCS} 2>/dev/null; " + cmd

print("gpr --auto with a title and description")
t, repo, env = make_world()
r = sh(functions('gpr_func --auto feat my-branch --title "feat: Add a thing" --description "## Summary\nDoes the thing."'), repo, env)
lines = [l for l in r.stdout.splitlines() if l.strip()]
try: j = json.loads(lines[-1])
except Exception: j = {}
check("stdout is exactly one JSON line", len(lines) == 1 and j.get("ok") is True, (r.stdout, r.stderr[-300:]))
check("JSON carries branch, worktree, pr_url, pr_number and title", j.get("branch") == "my-branch" and j.get("pr_number") == 7 and j.get("pr_url", "").endswith("/pull/7") and j.get("title") == "feat: Add a thing", j)
check("the worktree exists", os.path.isdir(j.get("worktree", "/nonexistent")), j)
args = open(t + "/gh-create.args").read().splitlines()
check("gh pr create got the title and the body verbatim", "feat: Add a thing" in args and any("Does the thing." in a for a in args) and "--draft" in args, args)
check("the first commit's subject is the title", git(repo + "/.worktrees/my-branch", "log", "-1", "--format=%s") == "feat: Add a thing")
check("the branch was pushed", "refs/heads/my-branch" in git(repo, "ls-remote", "--heads", "origin"))
check("the human log went to stderr, not stdout", "Worktree ready" in r.stderr and "Worktree ready" not in r.stdout)
check("exit code 0", r.returncode == 0, r.returncode)

print("gpr --auto never prompts")
t, repo, env = make_world()
r = sh(functions("gpr_func --auto feat"), repo, env, timeout=60)
j = json.loads([l for l in r.stdout.splitlines() if l.strip()][-1])
check("a missing branch is an error JSON, not a prompt", r.returncode != 0 and j["ok"] is False and "branch" in j["error"], (r.returncode, j))
r = sh(functions("gpr_func --auto"), repo, env, timeout=60)
j = json.loads([l for l in r.stdout.splitlines() if l.strip()][-1])
check("a missing type is an error JSON too", r.returncode != 0 and j["ok"] is False and "type" in j["error"], j)

print("gpr without the new flags behaves as before")
t, repo, env = make_world()
r = sh(functions("gpr_func feat plain-br"), repo, env)
args = open(t + "/gh-create.args").read().splitlines()
check("default title and template body", "feat: plain-br" in args and any("## Tickets" in a for a in args), args)
check("human output on stdout, no JSON", "Worktree ready" in r.stdout and not r.stdout.strip().endswith("}"), r.stdout[-200:])
t, repo, env = make_world(); open(t + "/body.md", "w").write("from a file\n")
r = sh(functions("gpr_func --auto fix from-file --body-file " + t + "/body.md --title 'fix: x'"), repo, env)
args = open(t + "/gh-create.args").read().splitlines()
check("--body-file supplies the body", any("from a file" in a for a in args), args)

print("gpc -m")
t, repo, env = make_world(); open(repo + "/new.txt", "w").write("x\n"); git(repo, "add", "new.txt")
r = sh(functions('gpc -m "Add new.txt" -d "Because we need it."'), repo, env)
check("commit subject and body are the caller's", git(repo, "log", "-1", "--format=%s") == "Add new.txt" and git(repo, "log", "-1", "--format=%b") == "Because we need it.", r.stdout[-300:])
check("pushed", git(repo, "rev-parse", "HEAD") == git(repo, "rev-parse", "origin/main") and "Successfully pushed" in r.stdout, r.stdout[-200:])

print("gpa --auto -m --no-review --json")
t, repo, env = make_world(); open(repo + "/feature.txt", "w").write("a feature\n")
r = sh(functions('gpa --auto -m "Add feature.txt" -d "Adds the feature file." --no-review --json'), repo, env, timeout=180)
lines = [l for l in r.stdout.splitlines() if l.strip()]
try: j = json.loads(lines[-1])
except Exception: j = {}
check("stdout is one JSON line with ok, commit, subject, pushed", len(lines) == 1 and j.get("ok") is True and j.get("pushed") is True and j.get("subject") == "Add feature.txt" and j.get("commit"), (r.stdout[-400:], r.stderr[-400:]))
check("the commit carries the caller's subject and body", git(repo, "log", "-1", "--format=%s|%b") == "Add feature.txt|Adds the feature file.", git(repo, "log", "-1", "--format=%s|%b"))
check("and it is on the remote", git(repo, "rev-parse", "HEAD") == git(repo, "rev-parse", "origin/main"))
check("no AI review ran", "AI code review skipped" in r.stderr and "Generating commit message" not in r.stderr, r.stderr[-300:])
t, repo, env = make_world()
r = sh(functions('gpa --auto -m "nothing" --no-review --json'), repo, env, timeout=60)
lines = [l for l in r.stdout.splitlines() if l.strip()]; j = json.loads(lines[-1])
check("no changes gives ok false and a non-zero exit", r.returncode != 0 and j["ok"] is False and j["commit"] is None, j)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
