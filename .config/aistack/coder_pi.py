#!/usr/bin/env python3
"""aidev's free builder: pi on the on-device Qwen3-Coder-30B-A3B (RFC 0002).

Ralph runs this as the `pi` agent's command (agent `coder-30b` in the run's config.toml) with pi's own arguments
(`--print --mode json --model coder/qwen3-coder-30b ...`) and the task prompt on stdin. It:

  - shares the 30B with the local-edit MCP server (local_edit_mcp.py): the same llama-server on port 8082, the same
    edit.lock, so one 30B job runs at a time on this machine, and the same last-used file and 2-minute idle unload;
  - points pi at that server through its own agent dir (models.json: provider `coder`, 32k context);
  - after pi exits, leaves a detached watcher (`local_edit_mcp.py --stop-when-idle`) that unloads the model once
    nothing has used it for LOCAL_EDIT_IDLE_S.

`coder_pi.py --hold -- <command...>` does the same for any other command (aider for `aidev -p` / `--direct`):
load the 30B, hold the lock while the command runs, then leave the idle watcher.

Exit codes: pi's (or the command's) own, or 3 when the 30B is not available (not downloaded on hosts below 32 GB,
or it failed to load); the driver then moves on to the next agent (Big Pickle, then Claude). Stdlib only.
"""

import fcntl
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.realpath(__file__))
PI = os.environ.get("CODER_PI_BIN") or shutil.which("pi") or "pi"
AGENT_DIR = os.environ.get("CODER_PI_AGENT_DIR") or os.path.expanduser("~/.cache/aistack-pi-coder")

_spec = importlib.util.spec_from_file_location("local_edit_mcp", os.path.join(HERE, "local_edit_mcp.py"))
le = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(le)


def write_models():
    os.makedirs(AGENT_DIR, exist_ok=True)
    cfg = {"providers": {"coder": {
        "baseUrl": le.BASE + "/v1", "api": "openai-completions", "apiKey": "sk-local",
        # Qwen3-Coder has no thinking mode; its window is the server's --ctx-size
        "models": [{"id": le.ALIAS, "reasoning": False, "contextWindow": le.CTX, "maxTokens": 8192}],
    }}}
    path = os.path.join(AGENT_DIR, "models.json")
    with open(path + ".tmp", "w") as fh:
        json.dump(cfg, fh, indent=1)
    os.replace(path + ".tmp", path)


def start_idle_watcher():
    subprocess.Popen([sys.executable, os.path.join(HERE, "local_edit_mcp.py"), "--stop-when-idle"],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def main(argv):
    hold = argv[:2] == ["--hold", "--"]
    cmd = argv[2:] if hold else [PI, *argv]
    if hold and not cmd:
        print("usage: coder_pi.py --hold -- <command...>", file=sys.stderr)
        return 2
    if not os.path.isfile(le.MODEL_FILE):
        print(f"coder-30b: the on-device coder model is not on this machine ({le.MODEL_FILE}); it is downloaded only "
              "on hosts with 32 GB or more", file=sys.stderr)
        return 3
    os.makedirs(le.STATE, exist_ok=True)
    with open(le.LOCK, "a") as lock:
        print("coder-30b: waiting for the 30B (one job at a time)", file=sys.stderr, flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)  # a local_edit or another builder may be using it
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
            env = dict(os.environ) if hold else {**os.environ, "PI_CODING_AGENT_DIR": AGENT_DIR}
            # stdin (the task prompt) and stdout (pi's JSON events for Ralph) pass straight through
            rc = subprocess.run(cmd, env=env).returncode
            stop.set()
            le.touch_last()
            return rc
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            start_idle_watcher()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
