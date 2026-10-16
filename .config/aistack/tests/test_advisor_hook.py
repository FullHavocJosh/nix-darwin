"""Tests for advisor_hook.py (advisor mode: Claude reads, the user makes changes). Runs the hook as Claude Code does,
with JSON on stdin. Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_advisor_hook.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(os.path.dirname(HERE), "advisor_hook.py")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="advisor-"))
STATE = T + "/state"
AWS_CONFIG = T + "/aws-config"
open(AWS_CONFIG, "w").write("[profile ops-ro]\nsso_role_name = OpsReadOnly\n[profile ops]\nsso_role_name = Admin\n")
HOME = os.path.expanduser("~")
UID = os.getuid()
ENV = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_ADVISOR", "CLAUDE_CODE_SESSION_ID")}
ENV.update(CLAUDE_ADVISOR_STATE=STATE, AWS_CONFIG_FILE=AWS_CONFIG)


def run(tool, tin, session="s1", env=None):
    ev = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tin, "session_id": session}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(ev), capture_output=True, text=True, env={**ENV, **(env or {})})
    out = p.stdout.strip()
    return json.loads(out)["hookSpecificOutput"] if out else None


def decision(tool, tin, **kw):
    d = run(tool, tin, **kw)
    return d["permissionDecision"] if d else None


def bash(cmd, **kw):
    return decision("Bash", {"command": cmd}, **kw)


def cli(*args, session="s1"):
    env = {**ENV, **({"CLAUDE_CODE_SESSION_ID": session} if session else {})}
    return subprocess.run([sys.executable, HOOK, *args], capture_output=True, text=True, env=env)


print("reads")
check("Read, Grep and Glob are left to Claude Code's own rules", all(decision(t, {"file_path": "/etc/hosts", "path": "/etc"}) is None for t in ("Read", "Grep", "Glob")))
check("reading a credential file is refused", decision("Read", {"file_path": HOME + "/.ssh/id_ed25519"}) == "deny")
check("WebFetch, Agent, Skill and AskUserQuestion are left alone", all(decision(t, {}) is None for t in ("WebFetch", "Agent", "Skill", "AskUserQuestion")))
check("read-only shell commands are allowed", all(bash(c) == "allow" for c in ("git status", "git log --oneline -5", "kubectl get pods", "ps aux", "cd /tmp && ls")))
check("read-only ssh is allowed", bash("ssh web1 'df -h'") == "allow" and bash("ssh -p 2222 web1 systemctl status nginx") == "allow")
check("read MCP tools are allowed", all(decision(t, {}) == "allow" for t in ("mcp__github__github_pr_list", "mcp__lumo__lumo_search", "mcp__terraform__providerDetails")))

print("changes")
d = run("Edit", {"file_path": "/Users/x/repo/a.py"})
check("Edit outside Claude's own files is refused, asking for a diff", d and d["permissionDecision"] == "deny" and "unified diff" in d["permissionDecisionReason"], d)
check("Write and NotebookEdit too", decision("Write", {"file_path": "/Users/x/repo/new.py"}) == "deny" and decision("NotebookEdit", {"notebook_path": "/x/n.ipynb"}) == "deny")
check("~/.claude/settings.json is not Claude's own file", decision("Edit", {"file_path": HOME + "/.claude/settings.json"}) == "deny")
check("the scratchpad, memory and plans stay writable", all(decision("Write", {"file_path": p}) is None for p in (
    f"/private/tmp/claude-{UID}/proj/sess/scratchpad/x.py", HOME + "/.claude/projects/p/memory/m.md", HOME + "/.claude/plans/p.md")))
check("~/.ai is writable (RFC 0003), ~/.ai/guard is not", all(decision("Write", {"file_path": p}, env={"AI_HOME": T + "/ai"}) is None for p in (
    T + "/ai/rfcs/2026-10-16-x.md", T + "/ai/aidev/p/plan/PLAN.txt")) and all(decision("Write", {"file_path": p}, env={"AI_HOME": T + "/ai"}) == "deny" for p in (
    T + "/ai/guard/advisor/s1.off", T + "/ai/guard", T + "/ai-other/x.md")))
d = run("Bash", {"command": "rm -rf build"})
check("a changing command is refused, asking for the command and an explanation", d and d["permissionDecision"] == "deny"
      and "! <command>" in d["permissionDecisionReason"] and "undo" in d["permissionDecisionReason"], d)
check("commits, installs and restarts are refused", all(bash(c) == "deny" for c in ("git " + "commit -m x", "brew install jq", "systemctl restart nginx", "darwin-rebuild switch")))
check("ssh with a changing remote command, or interactive ssh, is refused", bash("ssh web1 'rm /tmp/x'") == "deny" and bash("ssh web1") == "deny")
check("write MCP tools are refused", all(decision(t, {}) == "deny" for t in ("mcp__github__github_pr_create", "mcp__local-edit__local_edit", "mcp__oczen__oczen_edit", "mcp__hetzner__hetzner_reboot")))
check("a changing Monitor command is refused", decision("Monitor", {"command": "rm x"}) == "deny")
check("an unknown tool is refused", decision("EnterWorktree", {}) == "deny")
check("Claude cannot switch advisor mode off itself", bash("advisor off") == "deny")

print("aws")
check("aws reads need a -ro profile", bash("aws ec2 describe-instances --profile ops-ro") == "allow" and bash("aws ec2 describe-instances --profile ops") == "deny")
ssm = "aws ssm send-command --profile ops --instance-ids i-1 --document-name AWS-RunShellScript --parameters "
check("SSM send-command with read-only commands is allowed with any profile", bash(ssm + """'commands=["df -h","uptime"]'""") == "allow")
check("the JSON --parameters form works too", bash(ssm + """'{"commands":["systemctl status nginx"],"executionTimeout":["60"]}'""") == "allow")
check("SSM with a changing command is refused", bash(ssm + """'commands=["systemctl restart nginx"]'""") == "deny")
check("SSM with another document is refused", bash(ssm.replace("AWS-RunShellScript", "AWS-RunPowerShellScript") + """'commands=["dir"]'""") == "deny")
check("SSM with an extra flag (S3 output) is refused", bash(ssm + """'commands=["df -h"]' --output-s3-bucket-name b""") == "deny")
check("SSM results can be read with any profile", bash("aws ssm get-command-invocation --profile ops --command-id c --instance-id i-1") == "allow")
check("other SSM operations still need a -ro profile", bash("aws ssm get-parameter --name p --profile ops") == "deny")

print("switch")
check("CLAUDE_ADVISOR=off at launch turns it off", decision("Edit", {"file_path": "/x/a.py"}, env={"CLAUDE_ADVISOR": "off"}) is None)
r = cli("off")
check("`advisor off` turns it off for that session only", r.returncode == 0 and "off" in r.stdout
      and decision("Edit", {"file_path": "/x/a.py"}) is None and decision("Edit", {"file_path": "/x/a.py"}, session="s2") == "deny", r.stdout + r.stderr)
r = cli("on")
check("`advisor on` turns it back on", r.returncode == 0 and decision("Edit", {"file_path": "/x/a.py"}) == "deny", r.stdout)
check("`advisor status` reports", "is on" in cli("status").stdout)
check("outside Claude Code it explains instead of guessing a session", cli("off", session="").returncode == 1)
check("refusals are logged for tuning", os.path.exists(STATE + "/denied.jsonl"))
check("a broken guard fails closed", decision("Bash", {"command": "ls"}, env={"CLAUDE_ADVISOR_GUARD": T + "/missing.py"}) == "deny")

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
