#!/usr/bin/env python3
"""aidev's free builder: pi on the on-device gpt-oss-20b.

aidev's build-local pane runs this (with --hold) with pi's own arguments
(`--print --mode json --model coder/gpt-oss-20b ...`) and the task prompt on stdin. It:

  - shares the gpt-oss-20b (12 GB file, about 6.7 GB resident at ctx 32768) with the local-edit MCP server (local_edit_mcp.py): the same llama-server on port 8082, the same
    edit.lock, so one local-model job runs at a time on this machine, and the same last-used file and 2-minute idle unload;
  - points pi at that server through its own agent dir (models.json: provider `coder`, 32k context, reasoning effort low);
  - after pi exits, leaves a detached watcher (`local_edit_mcp.py --stop-when-idle`) that unloads the model once
    nothing has used it for LOCAL_EDIT_IDLE_S.

`coder_pi.py --hold -- <command...>` does the same for any other command (aider for `aidev -p` / `--direct`):
load the 30B, hold the lock while the command runs, then leave the idle watcher.

With AIDEV_REMOTE_BUILDER_URL and AIDEV_REMOTE_BUILDER_KEY_FILE set, a 2 s probe decides the path first: a
healthy remote server (the G14) runs pi (or the held command) against its own 30B, so no local lock, no idle
unload, and the local model need not even be on this machine; an unhealthy one prints one coder-30b stderr
line and falls through to the local path above. In hold mode the command gets a private copy of its pi agent
dir (PI_CODING_AGENT_DIR) with the remote models.json. A monitor thread re-probes every 5 s; after 3 failures
it stops the command and the wrapper exits 3 with a partial-edit warning (once: nothing returns to the remote).

Exit codes: pi's (or the command's) own, or 3 when the local model is not available (not downloaded on hosts below 24 GB,
or it failed to load); the driver then moves on to the next agent (Big Pickle, then Claude). Stdlib only.

The remote path runs only when AIDEV_REMOTE_BUILDER_URL is set explicitly (opt-in), the semi-local tier is
the default route to the G14. When the remote URL is not set explicitly, the local path runs with no network
probe.
"""

import fcntl
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.realpath(__file__))
PI = os.environ.get("CODER_PI_BIN") or shutil.which("pi") or "pi"
WORKTREE_GUARD = os.path.join(
    HERE, "..", "..", ".pi", "agent", "extensions", "worktree-guard.ts"
)
AGENT_DIR = os.environ.get("CODER_PI_AGENT_DIR") or os.path.join(
    os.path.expanduser(os.environ.get("AI_HOME") or "~/.ai"),
    "cache",
    "aistack-pi-coder",
)

_spec = importlib.util.spec_from_file_location(
    "local_edit_mcp", os.path.join(HERE, "local_edit_mcp.py")
)
le = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(le)
_spec = importlib.util.spec_from_file_location(
    "remote_builder", os.path.join(HERE, "remote_builder.py")
)
rb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rb)


def _write_agent_models(cfg):
    """pi's agent dir for one run: models.json as given, plus the compaction settings write."""
    os.makedirs(AGENT_DIR, exist_ok=True)
    path = os.path.join(AGENT_DIR, "models.json")
    with open(path + ".tmp", "w") as fh:
        json.dump(cfg, fh, indent=1)
    os.replace(path + ".tmp", path)
    # a builder that runs out of context must fail its attempt, not compact and lose the task (pi's overflow
    # recovery honours compaction.enabled too)
    path = os.path.join(AGENT_DIR, "settings.json")
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data["compaction"] = {**(data.get("compaction") or {}), "enabled": False}
    with open(path + ".tmp", "w") as fh:
        json.dump(data, fh, indent=1)
    os.replace(path + ".tmp", path)


def write_models():
    _write_agent_models(
        {
            "providers": {
                "coder": {
                    "baseUrl": le.BASE + "/v1",
                    "api": "openai-completions",
                    "apiKey": "sk-local",
                    # gpt-oss reasons at effort low through compat.chatTemplateKwargs; its window is the
                    # server's --ctx-size
                    "models": [le.pi_model_entry()],
                }
            }
        }
    )


def write_remote_models():
    """write_models' remote variant: the same agent dir, provider `coder` on the remote server. The key
    itself is never written; pi reads it from the key file at runtime."""
    _write_agent_models(rb.models_config(le.CTX))


def start_idle_watcher():
    subprocess.Popen(
        [sys.executable, os.path.join(HERE, "local_edit_mcp.py"), "--stop-when-idle"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _private_agent_dir(src):
    """Hold mode: a fresh dir that links every entry of the caller's pi agent dir `src` except models.json,
    which is the remote one; the caller's own dir stays untouched."""
    d = tempfile.mkdtemp(prefix="coder-pi-agent-")
    if src and os.path.isdir(src):
        for name in os.listdir(src):
            if name != "models.json":
                os.symlink(os.path.join(src, name), os.path.join(d, name))
    with open(os.path.join(d, "models.json"), "w") as fh:
        json.dump(rb.models_config(le.CTX), fh, indent=1)
    return d


def _watch_remote(proc, done, died):
    """Daemon monitor: probe the remote every AIDEV_REMOTE_BUILDER_MONITOR_S; after
    AIDEV_REMOTE_BUILDER_MONITOR_FAILS consecutive failures stop the command (kill after 3 s) and set `died`."""
    interval = float(os.environ.get("AIDEV_REMOTE_BUILDER_MONITOR_S") or 5)
    limit = int(os.environ.get("AIDEV_REMOTE_BUILDER_MONITOR_FAILS") or 3)
    fails = 0
    while not done.wait(interval):
        fails = 0 if rb.probe()[0] else fails + 1
        if fails >= limit:
            if proc.poll() is None:
                died.set()
                proc.terminate()
                try:
                    proc.wait(3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            return


def run_remote(cmd, hold):
    """Run cmd against the remote builder, once: 3 if the remote died mid-job (the driver moves to the next
    tier, nothing goes back to the remote), else the command's own code."""
    agent_dir = None
    env = dict(os.environ)
    if hold:
        agent_dir = _private_agent_dir(env.get("PI_CODING_AGENT_DIR"))
        env["PI_CODING_AGENT_DIR"] = agent_dir
    else:
        write_remote_models()
        env["PI_CODING_AGENT_DIR"] = AGENT_DIR
    try:
        # stdin (the task prompt) and stdout (pi's output) pass straight through
        proc = subprocess.Popen(cmd, env=env)
        done, died = threading.Event(), threading.Event()
        threading.Thread(
            target=_watch_remote, args=(proc, done, died), daemon=True
        ).start()
        rc = proc.wait()
        done.set()
        if died.is_set():
            rb.note(
                "remote builder died mid-job; the work dir may hold a partial edit, run git status and "
                "verify before retrying"
            )
            return 3
        return rc
    finally:
        if agent_dir:
            shutil.rmtree(agent_dir, ignore_errors=True)


def main(argv):
    hold = argv[:2] == ["--hold", "--"]
    cmd = argv[2:] if hold else [PI, "-e", WORKTREE_GUARD, *argv]
    if hold and not cmd:
        print("usage: coder_pi.py --hold -- <command...>", file=sys.stderr)
        return 2
    # The remote path is only used when AIDEV_REMOTE_BUILDER_URL is explicitly set
    remote_url = os.environ.get('AIDEV_REMOTE_BUILDER_URL', '').strip()
    if remote_url:
        ok, why = rb.probe()
        if ok:
            # the remote machine owns its model: no local lock, no idle unload, no local server
            return run_remote(cmd, hold)
        rb.note(f"remote builder unavailable ({why}), using the local 30B")
    if not os.path.isfile(le.MODEL_FILE):
        print(
            f"coder-30b: the on-device coder model is not on this machine ({le.MODEL_FILE}); it is downloaded only "
            "on hosts with 24 GB or more",
            file=sys.stderr,
        )
        return 3
    os.makedirs(le.STATE, exist_ok=True)
    with open(le.LOCK, "a") as lock:
        print(
            "coder-30b: waiting for the 30B (one job at a time)",
            file=sys.stderr,
            flush=True,
        )
        fcntl.flock(
            lock, fcntl.LOCK_EX
        )  # a local_edit or another builder may be using it
        try:
            err = le.ensure_server()
            if err:
                print(f"coder-30b: {err}", file=sys.stderr)
                return 3
            if not hold:
                write_models()
            le.touch_last()
            stop = threading.Event()

            def keep_alive():
                while not stop.wait(30):
                    le.touch_last()

            threading.Thread(target=keep_alive, daemon=True).start()
            env = (
                dict(os.environ)
                if hold
                else {**os.environ, "PI_CODING_AGENT_DIR": AGENT_DIR}
            )
            # stdin (the task prompt) and stdout (pi's output) pass straight through
            rc = subprocess.run(cmd, env=env).returncode
            stop.set()
            le.touch_last()
            return rc
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            start_idle_watcher()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
