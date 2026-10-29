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
    for k in ("AI_LOCAL_DEFAULT", "AI_LOCAL_ONLY"): e.pop(k, None)
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

print("gpr in a fork clone: origin's own repo and default branch, never the upstream parent's")
t, repo, env = make_world()
for url, want in [("https://github.com/me/fork.git", "me/fork"), ("git@github.com:me/fork.git", "me/fork"),
                  ("ssh://git@github.com/me/fork", "me/fork"), ("https://gitlab.com/me/fork.git", ""), ("/tmp/some/local.git", "")]:
    git(repo, "config", "remote.origin.url", url)
    r = sh(functions(f"_gpr_origin_repo {repo}"), repo, env)
    check(f"_gpr_origin_repo({url}) = {want!r}", r.stdout.strip() == want, r.stdout)
t = tempfile.mkdtemp(prefix="gitfork-"); bare = t + "/fork.git"; upstream = t + "/upstream.git"; repo = t + "/repo"; bin_ = t + "/bin"
subprocess.run(["git", "init", "-q", "--bare", bare]); subprocess.run(["git", "init", "-q", "--bare", upstream])
subprocess.run(["git", "clone", "-q", bare, repo], capture_output=True)
git(repo, "checkout", "-q", "-b", "develop"); open(repo + "/README.md", "w").write("fork\n")
git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "init"); git(repo, "push", "-q", "-u", "origin", "develop")
git(repo, "remote", "set-head", "origin", "develop")
git(repo, "remote", "add", "upstream", upstream)
git(repo, "config", f"url.{bare}.insteadOf", "https://github.com/me/fork.git")
git(repo, "config", "remote.origin.url", "https://github.com/me/fork.git")
os.makedirs(bin_)
open(bin_ + "/gh", "w").write(f"""#!/bin/sh
case "$1 $2" in
  "pr view") exit 1 ;;
  "pr list") echo "[]" ;;
  "pr create") printf '%s\\n' "$@" > {t}/gh-create.args; echo "https://github.com/me/fork/pull/3" ;;
esac
""")
os.chmod(bin_ + "/gh", 0o755)
env = {"PATH": bin_ + ":" + os.environ["PATH"]}
r = sh(functions('gpr_func --auto feat fork-br --title "feat: x" --description "y"'), repo, env)
try: j = json.loads([l for l in r.stdout.splitlines() if l.strip()][-1])
except Exception: j = {}
check("gpr succeeds with develop as the only default branch", j.get("ok") is True, (r.stdout[-300:], r.stderr[-400:]))
args = open(t + "/gh-create.args").read().splitlines() if os.path.exists(t + "/gh-create.args") else []
def flag(name): return args[args.index(name) + 1] if name in args else None
check("the PR is pinned to the fork repo", flag("--repo") == "me/fork", args)
check("the PR targets the fork's default branch", flag("--base") == "develop", args)
check("the PR head is the new branch", flag("--head") == "fork-br", args)
check("the worktree branch starts from develop", git(repo + "/.worktrees/fork-br", "merge-base", "HEAD", "develop") == git(repo, "rev-parse", "develop"))

print("gpa leaves formatting to a repo that has its own formatter")
t, repo, env = make_world()
open(repo + "/a.ts", "w").write("x\n")
def uses_other(path): return sh(functions(f"_repo_uses_other_formatter {path}; echo $?"), repo, env).stdout.strip()
check("no formatter config: prettier applies", uses_other(repo + "/a.ts") == "1")
open(repo + "/.oxfmtrc.jsonc", "w").write("{}\n")
check("an oxfmt config: prettier is skipped", uses_other(repo + "/a.ts") == "0")
open(repo + "/.prettierrc", "w").write("{}\n")
check("an oxfmt config and a prettier config: prettier applies", uses_other(repo + "/a.ts") == "1")
os.remove(repo + "/.prettierrc")
src = 'import { aaaaaaaaaa, bbbbbbbbbb, cccccccccc, dddddddddd, eeeeeeeeee, ffffffffff } from "some-package";\n'
open(repo + "/a.ts", "w").write(src)
r = sh(functions('gpa --auto -m "Add a.ts" --no-review --json'), repo, env, timeout=180)
lines = [l for l in r.stdout.splitlines() if l.strip()]
try: j = json.loads(lines[-1])
except Exception: j = {}
check("gpa commits and pushes", j.get("ok") is True and j.get("pushed") is True, (r.stdout[-300:], r.stderr[-300:]))
check("the file is committed as written, not rewrapped by prettier", open(repo + "/a.ts").read() == src and git(repo, "show", "HEAD:a.ts") == src.strip())

print("gpa runs the formatter the repo calls for")
t, repo, env = make_world()
def formatter(path): return sh(functions(f"_repo_formatter {path}"), repo, env).stdout.strip()
open(repo + "/a.ts", "w").write("x\n")
check("no formatter config: prettier", formatter(repo + "/a.ts") == "prettier")
open(repo + "/.oxfmtrc.jsonc", "w").write("{}\n")
check("an oxfmt config: oxfmt", formatter(repo + "/a.ts") == "oxfmt")
open(repo + "/.prettierrc", "w").write("{}\n")
check("a prettier config wins over an oxfmt config", formatter(repo + "/a.ts") == "prettier")
os.remove(repo + "/.prettierrc"); os.remove(repo + "/.oxfmtrc.jsonc")
open(repo + "/biome.json", "w").write("{}\n")
check("a biome config: biome", formatter(repo + "/a.ts") == "biome")
os.remove(repo + "/biome.json")

def stub(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write("#!/bin/sh\n" + body); os.chmod(path, 0o755)

def gpa_json(repo, env, msg):
    r = sh(functions(f'gpa --auto -m "{msg}" --no-review --json'), repo, env, timeout=180)
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    try: j = json.loads(lines[-1])
    except Exception: j = {}
    return j, r

# an oxfmt repo with a stub oxfmt in its node_modules: --check fails on BAD, writing replaces BAD with good
t, repo, env = make_world()
open(repo + "/.gitignore", "w").write("node_modules\n")
open(repo + "/.oxfmtrc.jsonc", "w").write("{}\n")
stub(repo + "/node_modules/.bin/oxfmt", 'cfg=$(ls .oxfmtrc.json* 2>/dev/null | head -1); [ -n "$cfg" ] || { echo no config >&2; exit 2; }\n'
     'if [ "$1" = "--check" ]; then grep -q BAD "$2" && exit 1; exit 0; fi\n'
     'sed "s/BAD/good/" "$1" > "$1.tmp" && mv "$1.tmp" "$1"\n')
stub(t + "/bin/prettier", '[ "$1" = "--version" ] && { echo 3.0.0; exit 0; }\necho "$@" >> ' + t + '/prettier.calls\nexit 0\n')
open(repo + "/b.ts", "w").write("const BAD = 1;\n")
j, r = gpa_json(repo, env, "Add b.ts")
check("an oxfmt repo: gpa commits and pushes", j.get("ok") is True and j.get("pushed") is True, (r.stdout[-300:], r.stderr[-300:]))
check("an oxfmt repo: the file is formatted by oxfmt from its config", git(repo, "show", "HEAD:b.ts") == "const good = 1;", git(repo, "show", "HEAD:b.ts"))
check("an oxfmt repo: the working copy has the formatted file", open(repo + "/b.ts").read() == "const good = 1;\n")
check("an oxfmt repo: prettier is not run", not os.path.exists(t + "/prettier.calls"))

# a repo without a formatter config falls back to prettier
t, repo, env = make_world()
stub(t + "/bin/prettier", 'if [ "$1" = "--version" ]; then echo 3.0.0; exit 0; fi\n'
     'if [ "$1" = "--check" ]; then grep -q BAD "$2" && exit 1; exit 0; fi\n'
     'sed "s/BAD/pretty/" "$2" > "$2.tmp" && mv "$2.tmp" "$2"\n')
open(repo + "/c.ts", "w").write("const BAD = 1;\n")
j, r = gpa_json(repo, env, "Add c.ts")
check("a repo with no formatter config: prettier formats the file", j.get("ok") is True and git(repo, "show", "HEAD:c.ts") == "const pretty = 1;", (git(repo, "show", "HEAD:c.ts"), r.stdout[-300:]))

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
