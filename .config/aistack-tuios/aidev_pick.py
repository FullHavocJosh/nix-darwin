#!/usr/bin/env python3
"""The dev layout's picker pane: choose what to start, while the checks for each choice run in the background.

    aidev_pick.py        draws the menu at once; every row shows "..." until its check answers, then a green check
                         (usable), a yellow ? (could not tell) or a red x (looks unusable). A red x never blocks a
                         choice: a check can be wrong.

Keys: 1-5 or up/down + enter start a choice, r runs the checks again, s leaves a shell, q quits. The rows below the
line (Zen, Go, OpenRouter) only report; they are what the cloud builders and fallbacks use.

  1 Claude (advisor): aidev's Claude and Lumo panes, Claude in advisor mode (AIDEV_TUIOS_ADVISOR=1)
  2 Claude (plan):    aidev start with planner forced to claude (AIDEV_TUIOS_PLANNER=claude)
  3 9B (advisor):     pi on the always-on llama-server (:8080), advisor prompt, read-only tools
  4 9B (plan):        aidev start with planner forced to local (AIDEV_TUIOS_PLANNER=local)
  5 30B (advisor):    pi on the Qwen3-Coder-30B (loaded on demand), advisor prompt, read-only tools
"""
import importlib.util
import json
import os
import select
import shutil
import subprocess
import sys
import termios
import threading
import time
import tty
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
AISTACK = os.path.expanduser(os.environ.get("AISTACK_DIR") or "~/.config/aistack")
AI_HOME = os.path.expanduser(os.environ.get("AI_HOME") or "~/.ai")
LLAMA = os.environ.get("LLAMA_CPP_HOST") or "http://127.0.0.1:8080"
NINE_B = os.environ.get("LOCAL_LLM_MODEL") or "qwen/qwen3.5-9b"
READ_TOOLS = "read,grep,find,ls"
GREEN, RED, YELLOW, DIM, RESET = "\x1b[32m", "\x1b[31m", "\x1b[33m", "\x1b[2m", "\x1b[0m"
MARK = {"ok": f"{GREEN}✓{RESET}", "bad": f"{RED}✗{RESET}", "maybe": f"{YELLOW}?{RESET}",
        "wait": f"{DIM}…{RESET}"}

# key, label, what it starts (None: a status row only)
ROWS = [("claude", "Claude (advisor)", True), ("claude-plan", "Claude (plan)", True),
        ("9b", "9B (advisor)", True), ("9b-plan", "9B (plan)", True), ("30b", "30B (advisor)", True),
        ("zen", "OpenCode Zen (free)", False), ("go", "OpenCode Go", False), ("openrouter", "OpenRouter", False)]
MIRROR = {"claude-plan": "claude", "9b-plan": "9b"}
state = {k: ("wait", "checking") for k, _l, _s in ROWS if k not in MIRROR}
lock = threading.Lock()


def set_state(key, status, detail):
    with lock:
        state[key] = (status, detail)


def run(cmd, timeout=15, env=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False, env=env)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None, ""


def get_json(url, headers=None, timeout=5):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "null")


def check_claude():
    if not shutil.which("claude"):
        return set_state("claude", "bad", "claude is not installed")
    
    # Try claude auth status up to twice
    for attempt in range(2):
        code, out = run(["claude", "auth", "status"])
        try:
            info = json.loads(out)
        except ValueError:
            # If we can't read the JSON, try again or give up
            if attempt == 0:
                continue  # Try again
            else:
                return set_state("claude", "maybe", f"could not read claude auth status (exit {code})")
        
        if info.get("loggedIn"):
            return set_state("claude", "ok", f"logged in ({info.get('authMethod')}, {info.get('subscriptionType')}); limits not visible")
        
        # If loggedIn is false, it could be a pane without keychain access
        # that wrongly reports loggedIn=false, so we should not treat it as bad
        return set_state("claude", "maybe", "auth status says not logged in; try it (r rechecks)")
    
    # If we get here, we tried twice and couldn't get valid JSON
    return set_state("claude", "maybe", f"could not read claude auth status (exit {code})")


def check_9b():
    try:
        health = get_json(LLAMA + "/health", timeout=3)
    except (OSError, ValueError):
        return set_state("9b", "bad", f"llama-server not reachable at {LLAMA}")
    if isinstance(health, dict) and health.get("status") == "ok":
        return set_state("9b", "ok", f"{NINE_B} at {LLAMA}")
    set_state("9b", "maybe", f"llama-server answered {health}")


def check_30b():
    path = os.environ.get("LOCAL_EDIT_MODEL_FILE") or os.path.expanduser(
        "~/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf")
    if not os.path.isfile(path):
        return set_state("30b", "bad", "model file missing (hosts below 32 GB do not download it)")
    try:
        get_json("http://127.0.0.1:8082/health", timeout=2)
        loaded = "loaded"
    except (OSError, ValueError):
        loaded = "not loaded; starts on first use (~25 s)"
    set_state("30b", "ok", loaded)


def check_zen_and_go():
    script = os.path.join(AISTACK, "zen_models.py")
    code, out = run([sys.executable, script, "status", "--private", "no", "--probe", "--all", "--json"], timeout=330)
    try:
        models = json.loads(out).get("models") or []
    except ValueError:
        models = []
    if code is None or not out.strip():
        set_state("zen", "maybe", "zen_models.py status gave no answer")
        return set_state("go", "maybe", "zen_models.py status gave no answer")
    for key, go in (("zen", False), ("go", True)):
        rows = [m for m in models if str(m.get("model", "")).startswith("opencode-go/") == go]
        states = {m.get("state") for m in rows}
        detail = ", ".join(f"{m.get('model')}: {m.get('state')}" for m in rows[:3]) or "no model offered"
        if "available" in states:
            set_state(key, "ok", detail)
        elif not rows or states <= {"exhausted"}:
            set_state(key, "bad", detail)
        else:
            set_state(key, "maybe", detail)


def check_openrouter():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return set_state("openrouter", "bad", "OPENROUTER_API_KEY is not set")
    try:
        data = (get_json("https://openrouter.ai/api/v1/auth/key", {"Authorization": f"Bearer {key}"}) or {}).get("data") or {}
    except (OSError, ValueError) as e:
        return set_state("openrouter", "maybe", f"key set; lookup failed ({e.__class__.__name__})")
    left, limit = data.get("limit_remaining"), data.get("limit")
    if left is None:
        return set_state("openrouter", "ok", "key valid, no spend limit")
    detail = f"${left:.2f} of ${limit:.2f} left"
    set_state("openrouter", "ok" if left > 0 else "bad", detail)


CHECKS = {"claude": check_claude, "9b": check_9b, "30b": check_30b, "openrouter": check_openrouter,
          "zen": check_zen_and_go}


def start_checks():
    for key in state:
        set_state(key, "wait", "checking")
    for fn in CHECKS.values():
        threading.Thread(target=fn, daemon=True).start()


def draw(cursor):
    with lock:
        snap = dict(state)
    out = ["\x1b[H\x1b[2J", "dev picker: what should this session start?\n\n"]
    room = max(10, shutil.get_terminal_size().columns - 34)
    STARTABLE = len([r for r in ROWS if r[2]])
    for i, (key, label, startable) in enumerate(ROWS):
        if i == STARTABLE:
            out.append(f"  {DIM}---- cloud (status only) ----{RESET}\n")
        status, detail = snap[MIRROR.get(key, key)]
        pointer = ">" if startable and i == cursor else " "
        num = f"{i + 1}" if startable else " "
        out.append(f" {pointer}{num} [{MARK[status]}] {label:<22} {DIM}{detail[:room]}{RESET}\n")
    out.append(f"\n {DIM}1-5 / arrows+enter start, r recheck, s shell, q quit; a red x never blocks a choice{RESET}\n")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def read_key():
    ready, _w, _x = select.select([sys.stdin], [], [], 0.25)
    if not ready:
        return None
    ch = os.read(sys.stdin.fileno(), 8).decode(errors="ignore")
    return {"\x1b[A": "up", "\x1b[B": "down", "\r": "enter", "\n": "enter"}.get(ch, ch)


def load_aidev():
    spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "aidev_tuios.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def advisor_prompt():
    """advisor-style.md without its frontmatter, for pi's --append-system-prompt, plus what a pi session can do."""
    text = open(os.path.join(AISTACK, "advisor-style.md")).read()
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    text = text.replace("A hook (`~/.config/aistack/advisor_hook.py`) refuses anything that changes something.",
                        "Your only tools are read, grep, find and ls; you cannot change anything.")
    path = os.path.join(AI_HOME, "cache", "aidev_pick", "advisor-prompt.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text.strip() + "\n\nThe user cannot see your tools, only your replies. Be short.\n")
    return path


def launch(key):
    cwd = os.getcwd()
    sys.stdout.write("\x1b[?25h\x1b[H\x1b[2J")
    sys.stdout.flush()
    if key == "claude":
        env = {**os.environ, "AIDEV_TUIOS_ADVISOR": "1", "AIDEV_TUIOS_NO_ATTACH": "1"}
        code = subprocess.run([sys.executable, os.path.join(HERE, "aidev_tuios.py"), "start"], cwd=cwd, env=env,
                              check=False).returncode
        if code:
            input("aidev start failed; Enter for a shell ")
        os.execvp("zsh", ["zsh", "-i"])
    elif key in ("claude-plan", "9b-plan"):
        env = {**os.environ, "AIDEV_TUIOS_NO_ATTACH": "1", "AIDEV_TUIOS_PLANNER": "claude" if key == "claude-plan" else "local"}
        code = subprocess.run([sys.executable, os.path.join(HERE, "aidev_tuios.py"), "start"], cwd=cwd, env=env,
                              check=False).returncode
        if code:
            input("aidev start failed; Enter for a shell ")
        os.execvp("zsh", ["zsh", "-i"])
    mod = load_aidev()
    cfg = mod.pane_configs(mod.project_root(cwd))
    prompt = advisor_prompt()
    common = ["--tools", READ_TOOLS, "--no-skills", "--append-system-prompt", prompt]
    if key == "9b":
        agent = os.path.join(AI_HOME, "cache", "aidev_pick", "pi-9b")
        os.makedirs(agent, exist_ok=True)
        with open(os.path.join(agent, "models.json"), "w") as fh:
            json.dump({"providers": {"llamacpp": {"baseUrl": LLAMA + "/v1", "api": "openai-completions",
                                                  "apiKey": "sk-local", "models": [{"id": NINE_B, "reasoning": False}]}}}, fh)
        argv = ["pi", "--provider", "llamacpp", "--model", NINE_B, "--name", "advisor 9b", "--thinking", "off"] + common
        os.execvpe("pi", argv, {**os.environ, "PI_CODING_AGENT_DIR": agent})
    model = mod.write_build_pi(cfg)
    argv = [sys.executable, os.path.join(AISTACK, "coder_pi.py"), "--hold", "--", "pi", "--model", model,
            "--name", "advisor 30b"] + common
    os.execvpe(argv[0], argv, {**os.environ, "PI_CODING_AGENT_DIR": cfg["pi_build"]})


def main():
    if not sys.stdin.isatty():
        print(__doc__)
        return 2
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    cursor, startable = 0, [i for i, r in enumerate(ROWS) if r[2]]
    start_checks()
    try:
        tty.setcbreak(fd)
        sys.stdout.write("\x1b[?25l")
        last = 0.0
        while True:
            if time.time() - last > 0.25:
                draw(cursor)
                last = time.time()
            key = read_key()
            if key in ("q", "\x03"):
                return 0
            if key == "s":
                break
            if key == "r":
                start_checks()
            elif key == "up":
                cursor = max(0, cursor - 1)
            elif key == "down":
                cursor = min(len(startable) - 1, cursor + 1)
            elif key in ("1", "2", "3", "4", "5"):
                cursor = int(key) - 1
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                launch(ROWS[cursor][0])
            elif key == "enter":
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                launch(ROWS[cursor][0])
            if key:
                last = 0.0
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\x1b[?25h")
    os.execvp("zsh", ["zsh", "-i"])


if __name__ == "__main__":
    sys.exit(main())
