#!/usr/bin/env python3
"""Claude Code PreToolUse hook (Edit|Write|MultiEdit|NotebookEdit): sends multi-file edits to the free edit tools.

Hand edits are billed output that stays in the conversation. When Claude starts on the third different file by hand
within one user request, this hook refuses that edit and points to local_edit (on-device Qwen3-Coder-30B) or
oczen_edit (OpenCode Zen Big Pickle). Measured: 7 edits in 6 files took 3 turns and $0.09 through local_edit, 18
turns and $0.16 by hand. Editing a file already edited in this request, by hand or by a delegation (fixing up
its result), is always allowed. Write is exempt and not counted: it carries the whole file Claude wrote, so a
delegate would only copy that text back (a 900 s timeout in practice). Editing a file Written in this request is
allowed too.

The edit goes through when delegating cannot help:
  - neither delegate exists on this host (no 30B model file, no OpenCode Zen key)
  - the file is not in a linked gpr worktree (both tools refuse main checkouts and paths outside a repository)
  - a local_edit or oczen_edit call already failed in this request
  - CLAUDE_EDIT_ROUTER=off
Registered in ~/.claude/settings.json by claudeSettingsCleanup (nix-modules/macos/packages-tui.nix). Stdlib only;
fails open (allows) on any error of its own.
"""

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
DELEGATES = {"mcp__local-edit__local_edit", "mcp__oczen__oczen_edit"}
MAX_HAND_FILES = int(os.environ.get("CLAUDE_EDIT_ROUTER_FILES", "3"))
HOME = os.path.expanduser("~")
STATE_DIR = os.environ.get("CLAUDE_EDIT_ROUTER_STATE") or os.path.join(os.environ.get("AI_HOME") or os.path.join(HOME, ".ai"), "guard", "edit-router")
CODER_MODEL = os.environ.get("LOCAL_EDIT_MODEL_FILE") or os.path.join(HOME, "models", "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf")


def zen_key_present():
    if os.environ.get("OPENCODE_ZEN_API_KEY"):
        return True
    for f in (".zshrc_envvars", ".zshrc_envvars_insecure", ".config/opencode/.env"):
        try:
            if "OPENCODE_ZEN_API_KEY" in open(os.path.join(HOME, f), errors="replace").read():
                return True
        except OSError:
            pass
    try:
        return bool((json.load(open(os.path.join(HOME, ".local/share/opencode/auth.json"))).get("opencode") or {}).get("key"))
    except (OSError, ValueError, AttributeError):
        return False


def in_linked_worktree(path):
    d = os.path.dirname(os.path.realpath(path)) or "."
    while not os.path.isdir(d):  # a new file in a new directory
        d = os.path.dirname(d)

    def rp(arg):
        r = subprocess.run(["git", "-C", d, "rev-parse", "--path-format=absolute", arg], capture_output=True, text=True)
        return os.path.realpath(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None

    git_dir, common = rp("--git-dir"), rp("--git-common-dir")
    return bool(git_dir and common and git_dir != common)


def reverse_lines(path, block=1 << 16):
    """Lines of a file from the end, so a long transcript is not read whole."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        pos, rest = f.tell(), b""
        while pos > 0:
            step = min(block, pos)
            pos -= step
            f.seek(pos)
            chunk = f.read(step) + rest
            lines = chunk.split(b"\n")
            rest = lines[0]
            yield from reversed(lines[1:])
        if rest:
            yield rest


def is_user_prompt(d):
    """A user entry that is not a tool result (a request, a slash command, a notification) starts a new turn."""
    if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
        return False
    c = (d.get("message") or {}).get("content")
    if isinstance(c, str):
        return bool(c.strip())
    if isinstance(c, list):
        return not any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c)
    return False


def last_prompt_key(transcript):
    """Identifies the current user request: the uuid (or a hash) of the last user prompt in the transcript."""
    for raw in reverse_lines(transcript):
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if is_user_prompt(d):
            return d.get("uuid") or hashlib.sha1(raw).hexdigest()
    return ""


def this_turn(transcript, current_id, cwd):
    """Since the last user request: files edited by hand, files a delegation covered or Write wrote, whether a
    delegation failed."""
    files, delegate_ids, delegated = set(), set(), set()
    results = {}
    for raw in reverse_lines(transcript):
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if is_user_prompt(d):
            break
        content = (d.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_result":
                results[c.get("tool_use_id")] = bool(c.get("is_error"))
            elif c.get("type") == "tool_use" and c.get("id") != current_id:
                name, inp = c.get("name"), c.get("input") or {}
                if name in EDIT_TOOLS:
                    p = inp.get("file_path") or inp.get("notebook_path")
                    if p:
                        (delegated if name == "Write" else files).add(os.path.realpath(p))
                elif name in DELEGATES:
                    delegate_ids.add(c.get("id"))
                    for f in ([inp["file"]] if inp.get("file") else []) + list(inp.get("files") or []):
                        delegated.add(os.path.realpath(os.path.join(cwd, os.path.expanduser(str(f)))))
    failed = any(results.get(i) for i in delegate_ids)
    return files, delegated, failed


def cleanup_old_state(max_age_s=86400):
    try:
        for f in os.listdir(STATE_DIR):
            p = os.path.join(STATE_DIR, f)
            if time.time() - os.path.getmtime(p) > max_age_s:
                os.remove(p)
    except OSError:
        pass


def main():
    inp = json.load(sys.stdin)
    # Write: the whole file is already in the call, so delegating it saves nothing
    if os.environ.get("CLAUDE_EDIT_ROUTER") == "off" or inp.get("tool_name") not in EDIT_TOOLS - {"Write"}:
        return
    ti = inp.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    transcript = inp.get("transcript_path")
    if not path or not transcript or not os.path.exists(transcript):
        return
    path = os.path.realpath(path)
    local_ok = os.path.isfile(CODER_MODEL)
    pickle_ok = zen_key_present()
    if not (local_ok or pickle_ok) or not in_linked_worktree(path):
        return
    files, delegated, failed = this_turn(transcript, inp.get("tool_use_id"), inp.get("cwd") or os.getcwd())
    # Parallel tool calls: Claude often sends several Edits in one response, and their hooks run before any of them is
    # in the transcript. So the hook also keeps its own record of the files it let through in this request.
    os.makedirs(STATE_DIR, exist_ok=True)
    key = inp.get("session_id") or hashlib.sha1(transcript.encode()).hexdigest()
    state_path = os.path.join(STATE_DIR, key + ".json")
    with open(state_path + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.load(open(state_path))
        except (OSError, ValueError):
            state = {}
        turn = last_prompt_key(transcript)
        if state.get("turn") != turn:
            state = {"turn": turn, "files": []}
        files |= set(state["files"])
        # fixing up a file a delegation edited (or Write wrote) is the review step, not a new hand edit
        allow = failed or path in files or path in delegated or len(files | {path}) < MAX_HAND_FILES
        if allow:
            if path not in state["files"]:
                state["files"].append(path)
            with open(state_path + ".tmp", "w") as fh:
                json.dump(state, fh)
            os.replace(state_path + ".tmp", state_path)
    cleanup_old_state()
    if allow:
        return
    tools = " or ".join(t for t, ok in (("local_edit", local_ok), ("oczen_edit", pickle_ok)) if ok)
    reason = (f"This would be file {len(files) + 1} edited by hand in this request. Hand the remaining changes to "
              f"{tools} instead, one call per file: the file, ideally start_line/end_line for the part to change, an exact "
              "instruction ending with 'Change nothing else.', and a test_cmd; then review the diff it returns. Prefer local_edit (on-device). "
              "Pure pattern replacements can be one sed or python command. If the delegate fails, hand edits are "
              "allowed again for the rest of this request.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never block an edit because the router itself broke
