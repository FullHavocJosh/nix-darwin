#!/usr/bin/env python3
"""Advisor mode for Claude Code: Claude reads, searches and reviews; the user makes every change.

A PreToolUse hook on every tool. Reads go through (files, read-only shell commands, read-only ssh, AWS and MCP
calls, Lumo, WebFetch, subagents). Anything that changes something is refused, and the refusal tells Claude to hand
the user the exact command or diff with an explanation, so the user runs it (`! <command>`) and learns from it.

What counts as read-only comes from ainfo's guard (.config/ainfo/ainfo_guard.py): default deny, a list of read-only
shell commands with argument checks (git, gh, kubectl, terraform, aws with a *-ro profile, ...), ssh only with a
remote command that passes the same check, and MCP tools judged by the words in their names. On top of it, advisor
mode allows:
  - more built-in tools (WebFetch, Agent, Skill, AskUserQuestion, plan mode, tasks, artifacts)
  - Edit/Write only in Claude's own files: the session scratchpad, ~/.claude/projects/*/memory, ~/.claude/plans
  - `aws ssm send-command --document-name AWS-RunShellScript` with any profile when every command in it passes the
    read-only check, and reading the results (get-command-invocation, list-command-invocations, list-commands,
    describe-instance-information) with any profile

On by default in every session. Off:
  - for one session: the user runs `! advisor off` (`! advisor on` turns it back on; `! advisor status`)
  - at launch: CLAUDE_ADVISOR=off claude
Claude cannot turn it off itself: `advisor` is not a read-only command, and the state directory is outside the
paths it may write. Fails closed: a broken guard refuses the call. Registered by claudeAdvisorSetup
(nix-modules/macos/packages-tui.nix), which also links ~/.local/bin/advisor here. Stdlib only.
"""

import importlib.util
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
HOME = os.path.expanduser("~")
STATE_DIR = os.environ.get("CLAUDE_ADVISOR_STATE") or os.path.join(HOME, ".cache", "advisor")
GUARD = os.environ.get("CLAUDE_ADVISOR_GUARD") or os.path.join(os.path.dirname(HERE), "ainfo", "ainfo_guard.py")

READ_TOOLS = {
    "Read", "Grep", "Glob", "LS", "LSP", "ToolSearch", "WebFetch", "Agent", "Task", "Skill", "AskUserQuestion",
    "EnterPlanMode", "ExitPlanMode", "TodoWrite", "TaskCreate", "TaskGet", "TaskList", "TaskUpdate", "TaskOutput",
    "TaskStop", "BashOutput", "KillShell", "ScheduleWakeup", "SendMessage", "ListAgents", "ListMcpResourcesTool",
    "ReadMcpResourceTool", "ReadMcpResourceDirTool", "Artifact", "ArtifactComments", "ArtifactData", "SendFeedback",
    "EndConversation", "CronCreate", "CronDelete", "CronList", "PushNotification",
}  # fmt: skip
PATH_TOOLS = {"Read": "file_path", "Grep": "path", "Glob": "path", "LS": "path"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

SSM_READS = {"get-command-invocation", "list-command-invocations", "list-commands", "describe-instance-information"}
SSM_SEND_FLAGS = {"--instance-ids", "--targets", "--document-name", "--parameters", "--comment", "--timeout-seconds",
                  "--max-concurrency", "--max-errors", "--profile", "--region", "--output", "--query"}  # fmt: skip
SSM_BOOL_FLAGS = {"--no-cli-pager", "--no-paginate"}
SSM_PARAM_KEYS = {"commands", "workingDirectory", "executionTimeout"}


def load_guard():
    spec = importlib.util.spec_from_file_location("ainfo_guard", GUARD)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    return g


def own_file(path):
    """Claude's own files: the session scratchpad, its memory and its plans."""
    p = os.path.realpath(os.path.expanduser(str(path)))
    uid = os.getuid()
    roots = [f"/private/tmp/claude-{uid}/", f"/tmp/claude-{uid}/", os.path.join(HOME, ".claude", "plans") + "/"]
    if any(p.startswith(r) for r in roots):
        return True
    return bool(re.match(re.escape(os.path.join(HOME, ".claude", "projects")) + r"/[^/]+/memory/", p))


def ssm_commands(raw):
    """The command list of AWS-RunShellScript --parameters: JSON, or commands=[...] / commands=<one command>."""
    raw = raw.strip()
    if raw.startswith("{"):
        obj = json.loads(raw)
    else:
        key, eq, val = raw.partition("=")
        if not eq:
            raise ValueError("no key=value")
        val = val.strip()
        obj = {key.strip(): json.loads(val) if val.startswith("[") else [val]}
    if not isinstance(obj, dict) or "commands" not in obj or set(obj) - SSM_PARAM_KEYS:
        raise ValueError("only commands, workingDirectory and executionTimeout")
    cmds = obj["commands"]
    cmds = [cmds] if isinstance(cmds, str) else cmds
    if not isinstance(cmds, list) or not cmds or not all(isinstance(c, str) for c in cmds):
        raise ValueError("commands must be a list of strings")
    return cmds


def make_aws_check(g):
    def aws_check(args):
        if any("file://" in a or "fileb://" in a for a in args):
            return "aws file:// arguments are not allowed"
        pos, flags, i = [], {}, 0
        value_flags = g.AWS_VALUE_GLOBALS | SSM_SEND_FLAGS
        while i < len(args):
            a = args[i]
            if a.startswith("--"):
                name, eq, val = a.partition("=")
                if not eq and name in value_flags:
                    val = args[i + 1] if i + 1 < len(args) else ""
                    i += 1
                flags[name] = val
            else:
                pos.append(a)
            i += 1
        if pos[:1] != ["ssm"] or len(pos) < 2 or pos[1] not in SSM_READS | {"send-command"}:
            return g.aws_check(args)
        bad = next((f for f in flags if f in g.AWS_BAD_GLOBALS), None)
        if bad:
            return f"aws {bad} is not allowed"
        if pos[1] in SSM_READS:
            return None
        other = next((f for f in flags if f not in SSM_SEND_FLAGS | SSM_BOOL_FLAGS), None)
        if other:
            return f"aws ssm send-command {other} is not allowed"
        if flags.get("--document-name") != "AWS-RunShellScript":
            return "aws ssm send-command may only run --document-name AWS-RunShellScript"
        try:
            cmds = ssm_commands(flags.get("--parameters", ""))
        except ValueError as e:
            return f"cannot read the SSM --parameters ({e}); pass commands as a JSON list"
        for c in cmds:
            why = g.check_shell(c)
            if why:
                return f"SSM command {c!r}: {why}"
        return None

    return aws_check


def decide(ev, g):
    """(decision, reason): decision is "allow", "deny" or None (leave it to Claude Code's own permission rules)."""
    tool, tin = ev.get("tool_name", ""), ev.get("tool_input") or {}
    if tool in READ_TOOLS:
        key = PATH_TOOLS.get(tool)
        if key and tin.get(key) and g.secret_path(tin[key]):
            return "deny", f"{tin[key]} looks like a credential file; ask the user for what you need from it"
        return None, ""
    if tool in EDIT_TOOLS:
        path = tin.get("file_path") or tin.get("notebook_path") or ""
        if path and own_file(path):
            return None, ""
        return "deny", (
            f"Advisor mode: the user makes changes to {path or 'files'}. Do not retry or work around this. Show the "
            "change as a unified diff with file:line (or the exact new text for a new file), explain what it changes "
            "and why, and how to check it. Then wait, and re-read the file to review it once they say it is done.")
    if tool in ("Bash", "Monitor"):
        cmd = str(tin.get("command") or "")
        if tool == "Monitor" and not cmd:
            return None, ""  # a WebSocket watch
        why = g.check_shell(cmd)
        if why is None:
            return "allow", ""
        return "deny", (
            f"Advisor mode: {why}. Do not run it or work around it. Give the user the exact command in a code block, "
            "to run as `! <command>`, and explain what each part does, what it changes, how to verify it and how to "
            "undo it. Then review the output they get. If it only reads and was refused wrongly, say so.")
    if tool.startswith("mcp__"):
        why = g.mcp_decision(tool, tin)
        if why is None:
            return "allow", ""
        return "deny", (
            f"Advisor mode: {why}. Do not call it or work around it. Tell the user the exact call (tool and "
            "arguments) or the equivalent steps or CLI command, what it changes, and how to verify it; they decide.")
    return "deny", (f"Advisor mode: {tool} is not on the advisor list. Do not work around it; tell the user what you "
                    "wanted to do and why, as a command or steps they can run.")


def session_off(session):
    return bool(session) and os.path.exists(os.path.join(STATE_DIR, f"{session}.off"))


def log_denial(ev, reason):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        p = os.path.join(STATE_DIR, "denied.jsonl")
        if os.path.exists(p) and os.path.getsize(p) > 1 << 20:
            os.replace(p, p + ".1")
        with open(p, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), "tool": ev.get("tool_name"), "input": ev.get("tool_input"),
                                "reason": reason[:300]}) + "\n")
    except OSError:
        pass


def hook():
    ev = json.load(sys.stdin)
    if os.environ.get("CLAUDE_ADVISOR") == "off" or session_off(ev.get("session_id")):
        return
    try:
        g = load_guard()
        g.READ_ONLY_WORDS["aws"] = make_aws_check(g)  # this module's copy only; ainfo loads its own
        decision, reason = decide(ev, g)
    except Exception as e:
        decision, reason = "deny", f"advisor hook error ({e}); the user can run `! advisor off` to get past it"
    if decision is None:
        return
    if decision == "deny":
        log_denial(ev, reason)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                             "permissionDecisionReason": reason or "advisor: read-only"}}))


def cli(args):
    """`advisor on|off|status` for the current Claude session, run by the user as `! advisor off`."""
    session = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    cmd = args[0] if args else "status"
    if cmd not in ("on", "off", "status"):
        print("usage: advisor on|off|status   (inside Claude Code: ! advisor off)", file=sys.stderr)
        return 2
    if not session:
        print("advisor: no CLAUDE_CODE_SESSION_ID; run it inside Claude Code as `! advisor off`, or start Claude with "
              "CLAUDE_ADVISOR=off", file=sys.stderr)
        return 1
    flag = os.path.join(STATE_DIR, f"{session}.off")
    if cmd == "off":
        os.makedirs(STATE_DIR, exist_ok=True)
        for f in os.listdir(STATE_DIR):  # switches of sessions that ended long ago
            p = os.path.join(STATE_DIR, f)
            if f.endswith(".off") and time.time() - os.path.getmtime(p) > 7 * 86400:
                os.remove(p)
        open(flag, "w").close()
    elif cmd == "on" and os.path.exists(flag):
        os.remove(flag)
    off = os.environ.get("CLAUDE_ADVISOR") == "off" or os.path.exists(flag)
    print(f"advisor mode is {'off' if off else 'on'} for this session"
          + (" (CLAUDE_ADVISOR=off at launch)" if os.environ.get("CLAUDE_ADVISOR") == "off" else ""))
    return 0


if __name__ == "__main__":
    # ~/.local/bin/advisor links here: run by that name (or with arguments) it is the on/off switch, not the hook
    if sys.argv[1:] or os.path.basename(sys.argv[0]) == "advisor":
        sys.exit(cli(sys.argv[1:]))
    try:
        hook()
    except Exception as e:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": f"advisor hook error ({e})"}}))
