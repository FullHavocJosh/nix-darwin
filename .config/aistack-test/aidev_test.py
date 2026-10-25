#!/usr/bin/env python3
"""aidev_test: aidev rebuilt on tuios, with every layer a live, interactive model pane (RFC
~/.ai/rfcs/2026-10-25-aidev-tuios-test.md). A test copy: it shares no names, state or config with aidev.

    aidev_test.py start [--resume] [--no-research] [task words...]   open the layers in this tuios session, or
                                                                      create or attach session aidev_test-<repo>
    aidev_test.py driver <project>                                    the driver loop (in the session's driver pane)
    aidev_test.py ai [-c] [message words...]                          ai_test: one Claude pane in session ai_test-<dir>
    aidev_test.py status [<project>]                                  print the latest run's state

One workspace per layer. Started inside tuios, the layers open in that session on its lowest free workspaces, beside
your own windows; outside tuios (or with AIDEV_TEST_OWN_SESSION=1) in session aidev_test-<repo>, numbered:

    1 research   pi on the local 9B: budgeted repo_* research, then `handoff` writes plan/brief.md
    2 plan       interactive Claude (advisor mode): writes plan/prd.json and plan/verify.json
    3 build      interactive builder: pi on the on-device 30B, else OpenCode on a free Zen model;
                 build-pickle / build-claude panes only when the person picks escalation
    4 review     interactive Claude (advisor mode): writes reviews/<run>.md, first line Verdict: PASS|FAIL
    5 dev        nvim / tuicr / zsh in the work dir
    9 driver     this script's loop (no model)

Rules the design rests on:
  - Files carry content, the driver reads only files: brief, plan, task prompts, verify output and reviews live in
    the state dir (~/.ai/aidev_test/<project>-<hash>). tuios mail is lost on a daemon restart, so it is never the
    source of truth; the driver uses it only to tell the person things.
  - Only the driver types into panes (`tuios queue`). Every model pane holds the `read` grant alone, so no model can
    type into, mail or start another pane.
  - The harness decides "done": the driver runs each task's verify commands itself, with shlex.split and no shell.
  - Every choice that costs money or changes scope goes to the person with `tuios ask-human`.
"""

import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.realpath(__file__))
HOME = os.path.expanduser("~")
AI_HOME = os.path.expanduser(os.environ.get("AI_HOME") or "~/.ai")
AISTACK = os.path.expanduser(os.environ.get("AISTACK_DIR") or "~/.config/aistack")
TEST_HOME = os.path.expanduser(os.environ.get("AIDEV_TEST_HOME") or os.path.join(AI_HOME, "aidev_test"))
CACHE = os.path.join(AI_HOME, "cache", "aidev_test")
# tuios on macOS reads ~/Library/Application Support/tuios unless XDG_CONFIG_HOME is set; the stowed config is in
# ~/.config/tuios. Every tuios call of the test stack sets it, so the daemon always starts on that config. HERDR_*
# is dropped: a daemon started from a herdr pane would hand herdr's variables on to every tuios pane.
TENV = {**{k: v for k, v in os.environ.items() if not k.startswith("HERDR_")},
        "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")}

CLAUDE_MODEL = os.environ.get("AIDEV_TEST_CLAUDE_MODEL") or os.environ.get("AISTACK_CLAUDE_MODEL") or "sonnet"
CLAUDE_EFFORT = os.environ.get("AIDEV_TEST_CLAUDE_EFFORT") or os.environ.get("AISTACK_CLAUDE_EFFORT") or "medium"
LOCAL_ENDPOINT = os.environ.get("LLAMA_CPP_HOST") or "http://127.0.0.1:8080"
LOCAL_MODEL = os.environ.get("LOCAL_LLM_MODEL") or "qwen/qwen3.5-9b"
CODER_FILE = os.path.expanduser(os.environ.get("LOCAL_EDIT_MODEL_FILE")
                                or "~/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf")
WORKER_ATTEMPTS = int(os.environ.get("AISTACK_WORKER_ATTEMPTS", "2"))
TURN_TIMEOUT_S = int(os.environ.get("AISTACK_ATTEMPT_TIMEOUT_S", "1500"))
VERIFY_TIMEOUT_S = int(os.environ.get("AISTACK_VERIFY_TIMEOUT_S", "300"))
ASK_TIMEOUT_MS = 3_600_000  # the most ask-human waits; the driver asks again after that
AT_REST = ("idle", "done", "errored")

# Each layer's workspace. A session of its own uses these numbers; a run started inside tuios opens in that session
# on its free workspaces instead (assign_workspaces). The map is kept in the run's state.json as "ws", so the driver
# and --resume use the same one.
WS_OWN = {"research": 1, "plan": 2, "build": 3, "build-pickle": 3, "build-claude": 3, "review": 4, "dev": 5,
          "driver": 9}
WS = dict(WS_OWN)
LAYERS = ("research", "plan", "build", "review", "dev", "driver")


# ---- the real stack, read-only --------------------------------------------------------------------------------
def load_ralph():
    """ralph_mcp.py from the real stack, for plan validation, worktree creation and file rules. AIDEV_TEST_HOME
    becomes its AISTACK_HOME, so every state_dir() it computes is the test stack's."""
    os.environ["AISTACK_HOME"] = TEST_HOME
    os.environ.pop("AISTACK_STATE_DIR", None)
    spec = importlib.util.spec_from_file_location("ralph_mcp", os.path.join(AISTACK, "ralph_mcp.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- tuios ----------------------------------------------------------------------------------------------------
def tuios(*args, timeout=60):
    """Run tuios; returns (exit code, stdout, stderr)."""
    try:
        r = subprocess.run(["tuios", *args], env=TENV, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, check=False)
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return r.returncode, r.stdout, r.stderr


def tuios_json(*args, timeout=60):
    _code, out, _err = tuios(*args, "--json", timeout=timeout)
    try:
        return json.loads(out) if out.strip() else {}
    except ValueError:
        return {}


def session_exists(name):
    data = tuios_json("ls")
    return any(s.get("name") == name for s in (data if isinstance(data, list) else []))


def windows(session):
    return tuios_json("list-windows", "-s", session).get("windows") or []


def window_named(session, name):
    for w in windows(session):
        if w.get("custom_name") == name:
            return w
    return None


def agent_state(session, name):
    w = window_named(session, name)
    return (w or {}).get("agent_state") or "gone"


def queue(session, name, text):
    """Type `text` as the next prompt of the agent in pane `name` once it is at rest (tuios queue). tuios queues only
    for an agent it recognises; for any other pane (OpenCode's `mini` TUI is one) the text is typed now, then Enter."""
    code, _out, err = tuios("queue", "-s", session, "-w", name, text)
    if code == 0:
        return True
    if "runs no agent" not in err:
        log(f"queue to {name} failed: {err.strip()[:300]}")
        return False
    code, _out, err = tuios("send-text", "-s", session, "-w", name, text)
    if code == 0:
        time.sleep(0.5)
        code, _out, err = tuios("send-keys", "-s", session, "-w", name, "enter")
    if code:
        log(f"typing into {name} failed: {err.strip()[:300]}")
    return code == 0


def tell_human(session, subject, text):
    tuios("send-agent-message", "-s", session, "-w", "human", "--subject", subject[:120], text[:7000])


ASK_MAX_BYTES = 160  # tuios refuses a longer ask-human question (invalid_params)


def short(text, limit=ASK_MAX_BYTES):
    data = text.encode()
    return text if len(data) <= limit else data[: limit - 3].decode(errors="ignore") + "..."


def ask_human(session, question, options, detail=None):
    """The person's answer, from the Inbox (Ctrl+B i). The question is short (tuios allows 160 bytes); `detail`, with
    paths and output, goes to the person as mail just before it. A question still pending after an hour is waited on
    again (--request-id), so the driver never gives up on the person."""
    if detail:
        tell_human(session, short(question, 120), detail)
    if os.environ.get("AIDEV_TEST_FAKE_HUMAN"):
        return fake_human(question, options)
    opts = [x for o in options for x in ("-o", o)]
    args = ("ask-human", "-s", session, "-w", "driver", short(question), *opts, "--timeout", str(ASK_TIMEOUT_MS),
            "--json")
    log(f"asking the person: {question} [{' / '.join(options)}]")
    _code, out, err = tuios(*args, timeout=ASK_TIMEOUT_MS / 1000 + 30)
    while True:
        try:
            data = json.loads(out)
        except ValueError:
            data = {}
        status = data.get("status")
        if status == "answered" and data.get("answer"):
            log(f"the person answered: {data['answer']}")
            return str(data["answer"])
        if status == "pending" and data.get("request_id"):
            _code, out, err = tuios("ask-human", "-s", session, "--request-id", data["request_id"], "--timeout",
                                    str(ASK_TIMEOUT_MS), "--json", timeout=ASK_TIMEOUT_MS / 1000 + 30)
            continue
        log(f"ask-human ended without an answer ({data.get('error') or status or err.strip()[:200]}); "
            "asking again in 10 s")
        time.sleep(10)
        _code, out, err = tuios(*args, timeout=ASK_TIMEOUT_MS / 1000 + 30)


def fake_human(question, options):
    """Tests only: answers come from lines appended to the file AIDEV_TEST_FAKE_HUMAN, because tuios lets only a
    client attached right now answer an ask-human (an attach nonce), which no script holds."""
    path = os.environ["AIDEV_TEST_FAKE_HUMAN"]
    log(f"asking the test file {path}: {question} [{' / '.join(options)}]")
    while True:
        try:
            lines = open(path).read().splitlines()
        except OSError:
            lines = []
        for i, line in enumerate(lines):
            if line.strip() in options:
                with open(path, "w") as fh:
                    fh.write("\n".join(lines[:i] + lines[i + 1:]) + "\n")
                log(f"the test file answered: {line.strip()}")
                return line.strip()
        time.sleep(2)


def attach(session):
    """Attach the person's terminal; inside tuios, switch the client instead of nesting a second one.
    AIDEV_TEST_NO_ATTACH=1 (scripts and tests) only prints the session name."""
    if os.environ.get("AIDEV_TEST_NO_ATTACH") == "1":
        print(session)
        return 0
    if os.environ.get("TUIOS_ENV"):
        if session != os.environ.get("TUIOS_SESSION"):
            tuios("switch-session", session)
        return 0
    os.execvpe("tuios", ["tuios", "attach", session], TENV)


def nested_in_herdr():
    """Inside a herdr pane (and not in tuios). AIDEV_TEST_ALLOW_NESTED=1 lets a script run anyway."""
    if os.environ.get("AIDEV_TEST_ALLOW_NESTED") == "1" or os.environ.get("TUIOS_ENV"):
        return False
    return bool(os.environ.get("HERDR_ENV") or os.environ.get("HERDR_PANE_ID"))


def name_ws(session, name):
    tuios("set-workspace-name", str(WS[name]), name, "-s", session)


# ---- project, state, run --------------------------------------------------------------------------------------
def project_root(path):
    r = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    return os.path.realpath(r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else path)


def is_main_checkout(project):
    def gd(flag):
        r = subprocess.run(["git", "-C", project, "rev-parse", "--path-format=absolute", flag],
                           capture_output=True, text=True, check=False)
        return r.stdout.strip() if r.returncode == 0 else None
    a, b = gd("--git-dir"), gd("--git-common-dir")
    return bool(a) and a == b


def project_key(project):
    return f"{os.path.basename(project)}-{hashlib.sha1(project.encode()).hexdigest()[:10]}"


def state_dir(project):
    return os.path.join(TEST_HOME, project_key(project))


def safe_name(text):
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in text)


def session_name(project):
    return "aidev_test-" + safe_name(os.path.basename(project))


def start_session(project):
    """The session a new run lives in: the tuios session aidev_test was started from, so the layers open as more
    workspaces beside your own windows, else aidev_test-<repo>. AIDEV_TEST_OWN_SESSION=1 always takes the latter."""
    here = os.environ.get("TUIOS_SESSION")
    if os.environ.get("TUIOS_ENV") and here and os.environ.get("AIDEV_TEST_OWN_SESSION") != "1":
        return here
    return session_name(project)


def assign_workspaces(run, session, own):
    """Fill WS for this run and keep it in the run. A session of its own uses WS_OWN. In a shared session each layer
    takes the lowest workspace with no window on it, so no layer lands beside your nvim or tuicr. Returns an error
    text when too few workspaces are free."""
    ws = run.data.get("ws")
    if not ws and own:
        ws = dict(WS_OWN)
    elif not ws:
        used = {w.get("workspace") for w in windows(session)}
        free = [n for n in range(1, 10) if n not in used]
        if len(free) < len(LAYERS):
            return (f"{session} has {len(free)} free workspaces and aidev_test needs {len(LAYERS)}. Close some, or "
                    "run with AIDEV_TEST_OWN_SESSION=1 for a session of its own.")
        ws = dict(zip(LAYERS, free))
        ws["build-pickle"] = ws["build-claude"] = ws["build"]
    run.data["ws"] = ws
    WS.update(ws)
    return None


def rj(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def wj(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as fh:
        json.dump(obj, fh, indent=1)
    os.replace(path + ".tmp", path)


LOG_PATH = None


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    if LOG_PATH:
        with open(LOG_PATH, "a") as fh:
            fh.write(line + "\n")


class Run:
    """runs/<id>/state.json: the phase, the tasks and the panes. Saved after every step, so a driver started again
    (aidev_test --resume, or the person restarting the driver pane) carries on where the last one stopped."""

    def __init__(self, project, run_id=None):
        self.project = project
        self.state = state_dir(project)
        runs = os.path.join(self.state, "runs")
        if not run_id:
            ids = sorted(os.listdir(runs)) if os.path.isdir(runs) else []
            live = [r for r in ids if rj(os.path.join(runs, r, "state.json"), {}).get("phase") not in
                    (None, "done", "aborted")]
            run_id = live[-1] if live else time.strftime("%Y%m%d-%H%M%S")
        self.id = run_id
        self.dir = os.path.join(runs, run_id)
        self.path = os.path.join(self.dir, "state.json")
        self.data = rj(self.path) or {"run_id": run_id, "project": project, "phase": "research", "tasks": {},
                                      "panes": {}, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}

    def save(self):
        wj(self.path, self.data)

    def event(self, kind, **kw):
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, "events.jsonl"), "a") as fh:
            fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, **kw}) + "\n")

    @property
    def plan_dir(self):
        return os.path.join(self.state, "plan")


# ---- per-pane configuration -----------------------------------------------------------------------------------
def pane_configs(project):
    """tuios hooks and MCP for this project's panes, generated under ~/.ai/cache/aidev_test, never in the stowed
    ~/.claude, ~/.pi or ~/.config/opencode (herdr's hooks live there)."""
    d = os.path.join(CACHE, project_key(project))
    claude_dir = os.path.join(d, "claude")
    os.makedirs(claude_dir, exist_ok=True)
    if not os.path.exists(os.path.join(claude_dir, "settings.json")):
        subprocess.run(["tuios", "integration", "install", "claude-code", "--no-skill"],
                       env={**TENV, "CLAUDE_CONFIG_DIR": claude_dir}, capture_output=True, text=True, check=False)
    mcp = os.path.join(d, "claude-mcp.json")
    wj(mcp, {"mcpServers": {"tuios": {"command": "tuios", "args": ["mcp"]}}})
    for name in ("pi-research", "pi-build"):
        pdir = os.path.join(d, name)
        os.makedirs(pdir, exist_ok=True)
        if not os.path.exists(os.path.join(pdir, "extensions", "tuios-agent-state.ts")):
            subprocess.run(["tuios", "integration", "install", "pi", "--no-skill"],
                           env={**TENV, "PI_CODING_AGENT_DIR": pdir}, capture_output=True, text=True, check=False)
    oc_dir = os.path.join(d, "opencode-xdg", "opencode")
    os.makedirs(oc_dir, exist_ok=True)
    if not os.path.exists(os.path.join(oc_dir, "plugins", "tuios-agent-state.js")):
        subprocess.run(["tuios", "integration", "install", "opencode", "--no-skill"],
                       env={**TENV, "XDG_CONFIG_HOME": os.path.dirname(oc_dir)}, capture_output=True, text=True,
                       check=False)
    return {"dir": d, "claude_settings": os.path.join(claude_dir, "settings.json"), "claude_mcp": mcp,
            "pi_research": os.path.join(d, "pi-research"), "pi_build": os.path.join(d, "pi-build"),
            "opencode_dir": oc_dir}


def write_research_pi(cfg, project):
    pdir = cfg["pi_research"]
    wj(os.path.join(pdir, "models.json"), {"providers": {"llamacpp": {
        "baseUrl": LOCAL_ENDPOINT + "/v1", "api": "openai-completions", "apiKey": "sk-local",
        "models": [{"id": LOCAL_MODEL, "reasoning": True, "compat": {"thinkingFormat": "qwen-chat-template"}}]}}})
    wj(os.path.join(pdir, "mcp.json"), {"mcpServers": {
        "aidev_test": {"command": sys.executable, "args": [os.path.join(HERE, "aidev_test_mcp.py")],
                       "env": {"RALPH_MCP_ROOTS": project, "AIDEV_TEST_HOME": TEST_HOME,
                               "AISTACK_RESEARCH_CALLS": os.environ.get("AISTACK_RESEARCH_CALLS", "16")},
                       "exposure": "direct", "timeout": 120,
                       "description": "aidev_test research tools (budgeted) and the handoff to the plan pane."},
        "tuios": {"command": "tuios", "args": ["mcp"], "exposure": "direct", "timeout": 60,
                  "description": "Read-only view of the other aidev_test panes."},
        "github": {"command": "npx", "args": ["-y", "@edjl/github-mcp"], "exposure": "direct", "timeout": 60,
                   "description": "Read-only GitHub lookups through the logged-in gh."}}})


def write_build_pi(cfg):
    spec = importlib.util.spec_from_file_location("local_edit_mcp", os.path.join(AISTACK, "local_edit_mcp.py"))
    le = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(le)
    wj(os.path.join(cfg["pi_build"], "models.json"), {"providers": {"coder": {
        "baseUrl": le.BASE + "/v1", "api": "openai-completions", "apiKey": "sk-local",
        "models": [{"id": le.ALIAS, "reasoning": False, "contextWindow": le.CTX, "maxTokens": 8192}]}}})
    return f"coder/{le.ALIAS}"


def zen_model(project):
    """The free Zen model for this repository, or None (no key, or nothing offered)."""
    r = subprocess.run(["gh", "repo", "view", "--json", "isPrivate", "-q", ".isPrivate"], cwd=project,
                       capture_output=True, text=True, check=False)
    private = "no" if r.returncode == 0 and r.stdout.strip() == "false" else "yes"  # unknown counts as private
    private = os.environ.get("AIDEV_TEST_REPO_PRIVATE") or private  # tests: a scratch repo has no GitHub remote
    r = subprocess.run([sys.executable, os.path.join(AISTACK, "zen_models.py"), "choose", "--private", private],
                       capture_output=True, text=True, check=False)
    try:
        return json.loads(r.stdout).get("model") or None
    except ValueError:
        return None


def prompt_text(name, **subst):
    text = open(os.path.join(HERE, f"layer-{name}.md")).read()
    for k, v in subst.items():
        text = text.replace(f"@@{k}@@", str(v))
    return text


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    return path


def write_script(run, name, body):
    """A pane's launcher: runs the layer, then leaves a shell in the pane with the line that starts it again."""
    path = os.path.join(run.dir, "bin", f"{name}.sh")
    write_text(path, "#!/bin/zsh\n# generated by aidev_test.py; runs in the tuios pane " + name + "\n"
               + body.rstrip() + "\n"
               + f"echo; echo '[aidev_test] {name} exited. Start it again: zsh {path}'\nexec zsh -i\n")
    os.chmod(path, 0o755)
    return path


def with_system_prompt(argv, sysp):
    """argv as a shell line, plus --append-system-prompt read from the file when the line runs (pi and claude both
    take the text, not a path)."""
    return " ".join(map(shlex.quote, argv)) + ' --append-system-prompt "$(<' + shlex.quote(sysp) + ')"'


def claude_body(run, cfg, name, system, first, cwd, advisor=True):
    """An interactive Claude Code pane that keeps one conversation: --session-id the first time, --resume after."""
    sid = run.data["panes"].setdefault(name, {}).setdefault("session_id", str(uuid.uuid4()))
    sysp = write_text(os.path.join(run.dir, "bin", f"{name}.system.md"), system)
    marker = os.path.join(run.dir, "bin", f"{name}.started")
    base = ["claude", "--settings", cfg["claude_settings"], "--mcp-config", cfg["claude_mcp"],
            "--model", CLAUDE_MODEL, "--effort", CLAUDE_EFFORT, "--add-dir", run.state, "-n", f"aidev_test {name}"]
    first_line = with_system_prompt(base + ["--session-id", sid], sysp) + " " + shlex.quote(first)
    again_line = with_system_prompt(base + ["--resume", sid], sysp)
    env = "" if advisor else "export CLAUDE_ADVISOR=off\n"
    return (f"{env}cd {shlex.quote(cwd)}\nif [[ -f {shlex.quote(marker)} ]]; then\n  {again_line}\nelse\n"
            f"  touch {shlex.quote(marker)}\n  {first_line}\nfi")


def open_pane(run, session, name, script, cwd, grants="read"):
    """A window for one layer on its workspace; does nothing when the window is already there."""
    if window_named(session, name):
        return False
    code, _out, err = tuios("new-window", name, "-s", session, "--workspace", str(WS[name]), "--cwd", cwd,
                            "--grants", grants, "--no-focus", "--", "/bin/zsh", script)
    if code:
        log(f"could not open the {name} pane: {err.strip()[:300]}")
        return False
    run.data["panes"].setdefault(name, {}).update(script=script, cwd=cwd, grants=grants,
                                                  opened=time.strftime("%H:%M:%S"))
    run.save()
    return True


# ---- layers ---------------------------------------------------------------------------------------------------
RESEARCH_TOOLS = [
    "mcp__aidev_test__repo_tree", "mcp__aidev_test__repo_read", "mcp__aidev_test__repo_grep",
    "mcp__aidev_test__handoff", "mcp__aidev_test__save_rfc", "mcp__tuios__tuios_list_agents",
    "mcp__tuios__tuios_capture_pane", "mcp__tuios__tuios_get_agent_state", "mcp__github__github_file_get",
    "mcp__github__github_pr_list", "mcp__github__github_pr_details", "mcp__github__github_issues_list",
]


def research_body(run, cfg, task):
    write_research_pi(cfg, run.project)
    sid = run.data["panes"].setdefault("research", {}).setdefault("session_id", str(uuid.uuid4()))
    sysp = write_text(os.path.join(run.dir, "bin", "research.system.md"),
                      prompt_text("research", PROJECT=run.project, PLAN_DIR=run.plan_dir))
    argv = ["pi", "--provider", "llamacpp", "--model", LOCAL_MODEL, "--name", "aidev_test research", "--no-skills",
            "--thinking", os.environ.get("AISTACK_RELAY_THINKING", "off"), "--tools", ",".join(RESEARCH_TOOLS),
            "--session-id", sid]
    line = with_system_prompt(argv, sysp)
    if task:
        line += " " + shlex.quote(f"REQUEST FROM THE USER: {task}")
    return f"cd {shlex.quote(run.project)}\nexport PI_CODING_AGENT_DIR={shlex.quote(cfg['pi_research'])}\n{line}"


def build_body(run, cfg, name):
    """The builder pane's launcher body, or None when no builder exists for `name`."""
    wd = run.data.get("work_dir") or run.project
    system = prompt_text("build", WORK_DIR=wd, RUN_DIR=run.dir)
    pane = run.data["panes"].setdefault(name, {})
    if name == "build-claude":
        pane["builder"] = f"Claude Code {CLAUDE_MODEL} (billed)"
        return claude_body(run, cfg, name, system, "Wait for the driver's first task message.", wd, advisor=False)
    sysp = write_text(os.path.join(run.dir, "bin", f"{name}.system.md"), system)
    if name == "build" and os.path.isfile(CODER_FILE):
        model = write_build_pi(cfg)
        sid = pane.setdefault("session_id", str(uuid.uuid4()))
        argv = [sys.executable, os.path.join(AISTACK, "coder_pi.py"), "--hold", "--", "pi", "--model", model,
                "--name", "aidev_test build", "--no-skills", "--session-id", sid]
        pane["builder"] = "on-device Qwen3-Coder-30B (free)"
        return (f"cd {shlex.quote(wd)}\nexport PI_CODING_AGENT_DIR={shlex.quote(cfg['pi_build'])}\n"
                + with_system_prompt(argv, sysp))
    model = run.data.get("zen_model") or zen_model(run.project)
    if not model:
        return None
    run.data["zen_model"] = model
    pane["builder"] = f"OpenCode {model} (free)"
    model = model if "/" in model else f"opencode/{model}"  # opencode wants provider/model
    first = f"Read your instructions in {sysp}, then wait for the driver's first task message."
    # OPENCODE_CONFIG_DIR adds the tuios state plugin to the user's own opencode config, for this pane only
    return (f"cd {shlex.quote(wd)}\nexport OPENCODE_CONFIG_DIR={shlex.quote(cfg['opencode_dir'])}\n"
            f"opencode mini --model {shlex.quote(model)} --prompt {shlex.quote(first)}")


def start_dev_workspace(run, session):
    wd = run.data.get("work_dir") or run.project
    for name, cmd in (("dev-nvim", "nvim"), ("dev-tuicr", "_tuicr_current_pr_test"), ("dev-zsh", "git status")):
        if window_named(session, name):
            continue
        tuios("new-window", name, "-s", session, "--workspace", str(WS["dev"]), "--cwd", wd, "--no-focus")
        tuios("send-text", "-s", session, "-w", name, cmd + "\n")
    name_ws(session, "dev")


# ---- driver ---------------------------------------------------------------------------------------------------
def task_order(prd):
    """Task ids in dependency order, lower priority number first among the ready ones."""
    stories = {s["id"]: s for s in prd.get("userStories", [])}
    done, order = set(), []
    while len(order) < len(stories):
        ready = [s for i, s in stories.items() if i not in done and set(s.get("dependsOn") or []) <= done]
        if not ready:
            order += [i for i in stories if i not in done]  # a cycle: validate() refuses it, keep the rest anyway
            break
        nxt = min(ready, key=lambda s: (s.get("priority", 99), s["id"]))
        order.append(nxt["id"])
        done.add(nxt["id"])
    return order


def run_verify(cmds, cwd, out_path):
    """Every command with shlex.split and no shell. (passed, text)."""
    parts, ok = [], True
    for cmd in [cmds] if isinstance(cmds, str) else cmds:
        try:
            r = subprocess.run(shlex.split(cmd), cwd=cwd, capture_output=True, text=True, timeout=VERIFY_TIMEOUT_S,
                               stdin=subprocess.DEVNULL, check=False)
            code, out = r.returncode, (r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            code, out = 124, f"timed out after {VERIFY_TIMEOUT_S} s"
        except (OSError, ValueError) as e:
            code, out = 127, str(e)
        parts.append(f"$ {cmd}\nexit {code}\n{out[-6000:]}")
        ok = ok and code == 0
    text = "\n\n".join(parts)
    write_text(out_path, text)
    return ok, text


def task_prompt(prd, story, verify_cmds, attempt_notes):
    verify_cmds = [verify_cmds] if isinstance(verify_cmds, str) else verify_cmds
    lines = [f"# Task {story['id']}: {story.get('title', '')}", "", f"Plan: {prd.get('name', '')}",
             str(prd.get("description") or ""), "", "## What to do", str(story.get("description") or ""), "",
             "## Done when"] + [f"- {c}" for c in story.get("acceptanceCriteria", [])] + [
             "", "## Checks the driver runs after your turn (no shell; each must exit 0)"] + [
             f"- `{c}`" for c in verify_cmds]
    if attempt_notes:
        lines += ["", "## Earlier attempts"] + attempt_notes
    lines += ["", "## Rules", "- Read the existing code first and follow its conventions.",
              "- Do this task only. No git commits, no files unrelated to it.",
              "- Run the checks above yourself before you stop.",
              "- When you need a decision you cannot safely make, ask the person in this pane and wait."]
    return "\n".join(lines) + "\n"


def wait_turn(session, name, timeout_s=TURN_TIMEOUT_S):
    """Wait until the agent in pane `name` has taken a turn and come to rest. Returns its last state, 'quiet',
    'timeout' or 'gone'. A pane that reports no state (OpenCode without its plugin) counts as at rest after 20 s
    with an unchanged screen."""
    start, seen_work, last_text, quiet_since = time.time(), False, None, time.time()
    while time.time() - start < timeout_s:
        st = agent_state(session, name)
        if st == "gone":
            return "gone"
        if st in ("working", "needs_input"):
            seen_work = True
        elif seen_work and st in AT_REST:
            return st
        if st in ("none", "unknown"):
            _c, text, _e = tuios("capture-pane", "-s", session, "-w", name, "--lines", "40")
            if text != last_text:
                if last_text is not None:
                    seen_work = True
                last_text, quiet_since = text, time.time()
            elif seen_work and time.time() - quiet_since > 20:
                return "quiet"
        time.sleep(3)
    return "timeout"


def wait_ready(session, name, timeout_s=300):
    """True once the agent in pane `name` is at rest: its reported state, or for a pane that reports none, a
    screen that has not changed for 10 s."""
    start, last_text, still_since = time.time(), None, time.time()
    while time.time() - start < timeout_s:
        st = agent_state(session, name)
        if st in ("idle", "done"):
            return True
        if st == "gone":
            return False
        if st in ("none", "unknown"):
            _c, text, _e = tuios("capture-pane", "-s", session, "-w", name, "--lines", "40")
            if text != last_text:
                last_text, still_since = text, time.time()
            elif time.time() - still_since > 10 and time.time() - start > 15:
                return True
        time.sleep(3)
    return False


def start_plan_pane(run, session, cfg, first):
    system = prompt_text("plan", PROJECT=run.project, PLAN_DIR=run.plan_dir)
    script = write_script(run, "plan", claude_body(run, cfg, "plan", system, first, run.project))
    if open_pane(run, session, "plan", script, run.project):
        name_ws(session, "plan")


def phase_research(run, session, cfg):
    brief = os.path.join(run.plan_dir, "brief.md")
    prd = os.path.join(run.plan_dir, "prd.json")
    since = run.data.setdefault("research_since", time.time())
    run.save()
    log("research: waiting for the research pane's handoff (plan/brief.md), or a plan written in the plan pane")
    while True:
        if os.path.exists(brief) and os.path.getmtime(brief) >= since - 1:
            break
        if os.path.exists(prd) and os.path.getmtime(prd) >= since - 1:
            break
        if window_named(session, "plan"):  # aidev_test --no-research: the plan pane is already open
            break
        time.sleep(3)
    has_brief = os.path.exists(brief) and os.path.getmtime(brief) >= since - 1
    first = (f"Read the research brief in {brief} and plan the work it describes." if has_brief
             else "Plan the work the person describes next.")
    start_plan_pane(run, session, cfg, first)
    run.data["phase"] = "plan"
    run.event("handoff", brief=brief if has_brief else None)
    run.save()
    tell_human(session, "plan pane open", f"Workspace {WS['plan']}: Claude plans in {run.plan_dir}. Talk to it there.")


def phase_plan(run, session, cfg, ralph):
    log("plan: watching plan/prd.json and plan/verify.json")
    checked = None
    while True:
        prd, verify, h = ralph.load_plan(run.project)
        if (prd is None and verify is None) or h == checked:
            time.sleep(3)
            continue
        if agent_state(session, "plan") == "working":
            time.sleep(3)  # Claude is still writing; check once it rests
            continue
        checked = h
        problems = ralph.validate(prd, verify)
        if problems:
            run.event("plan_problems", plan_hash=h, problems=problems)
            log(f"plan {h}: {len(problems)} problem(s); sent to the plan pane")
            queue(session, "plan", "aidev_test check: the plan files have problems. Fix them in the files:\n- "
                  + "\n- ".join(map(str, problems[:12])))
            continue
        ralph.save_plan_text(run.project, ralph.present_plan(prd, verify))
        log(f"plan {h} is valid: {len(prd['userStories'])} task(s). Asking the person.")
        ans = ask_human(session, f"aidev_test: plan '{prd.get('name')}' ({len(prd['userStories'])} tasks) is valid. "
                        "Start the build?", ["start", "keep planning"],
                        detail=f"The plan: {run.plan_dir}/PLAN.txt (prd.json, verify.json beside it).")
        h2 = ralph.load_plan(run.project)[2]
        if ans == "start" and h2 == h:
            run.data.update(phase="build", plan_hash=h)
            run.event("plan_confirmed", plan_hash=h)
            run.save()
            return
        if ans == "start":
            log("the plan changed while you were asked; checking the new one")


def ensure_builder(run, session, cfg, name):
    if window_named(session, name):
        return True
    body = build_body(run, cfg, name)
    if not body:
        log(f"no builder for {name}: no on-device 30B and no free Zen model")
        return False
    open_pane(run, session, name, write_script(run, name, body), run.data.get("work_dir") or run.project)
    name_ws(session, "build")
    log(f"{name}: starting {run.data['panes'][name].get('builder')}; waiting until it is ready")
    if not wait_ready(session, name):
        log(f"{name}: no ready state after 5 minutes; sending the first task anyway")
    return True


def escalation_options(run, builder):
    options = ["retry", "skip", "abort"]
    if builder != "build-claude":
        options.insert(1, "escalate: claude (billed)")
    if builder == "build" and os.path.isfile(CODER_FILE) and (run.data.get("zen_model") or zen_model(run.project)):
        options.insert(1, "escalate: pickle")
    return options


def phase_build(run, session, cfg, ralph):
    prd, verify, _h = ralph.load_plan(run.project)
    if not run.data.get("work_dir"):
        os.environ["AISTACK_WORKTREE_MODE"] = os.environ.get("AIDEV_TEST_WORKTREE_MODE") or (
            "create" if is_main_checkout(run.project) else "none")
        os.environ["AISTACK_TIERS"] = "aidev_test: research local 9B, plan Claude (interactive), build interactive"
        wd, created, err = ralph.ensure_workdir(run.project, prd, verify)
        if err:
            log(err)
            ans = ask_human(session, "aidev_test: creating the worktree failed. Work in the project itself?",
                            ["use the project", "abort"], detail=err)
            if ans != "use the project":
                run.data["phase"] = "aborted"
                run.save()
                return
            wd, created = run.project, False
        run.data["work_dir"] = wd
        run.event("work_dir", work_dir=wd, created=created)
        run.save()
    start_dev_workspace(run, session)
    builder = run.data.get("builder") or "build"
    if not ensure_builder(run, session, cfg, builder):
        ans = ask_human(session, "aidev_test: no free builder here. Build with Claude (billed)?", ["claude", "abort"],
                        detail="No on-device 30B on this host and no free OpenCode Zen model.")
        if ans != "claude":
            run.data["phase"] = "aborted"
            run.save()
            return
        builder = run.data["builder"] = "build-claude"
        ensure_builder(run, session, cfg, builder)
    stories = {s["id"]: s for s in prd["userStories"]}
    for tid in task_order(prd):
        t = run.data["tasks"].setdefault(tid, {"status": "pending", "attempts": 0, "notes": []})
        if t["status"] in ("verified", "skipped"):
            continue
        while True:
            t["attempts"] += 1
            run.save()
            path = write_text(os.path.join(run.dir, "tasks", f"{tid}.md"),
                              task_prompt(prd, stories[tid], verify[tid], t["notes"]))
            log(f"{tid}: attempt {t['attempts']} in {builder}")
            sent = queue(session, builder, f"aidev_test task {tid}: read {path} and do exactly that task. "
                         "Stop when its checks pass.")
            end = wait_turn(session, builder) if sent else "not delivered"
            out = os.path.join(run.dir, "tasks", f"{tid}-verify-{t['attempts']}.txt")
            ok, _text = run_verify(verify[tid], run.data["work_dir"], out)
            run.event("verify", task=tid, attempt=t["attempts"], ok=ok, turn=end, output=out)
            if ok:
                t["status"] = "verified"
                run.save()
                log(f"{tid}: verified")
                break
            t["notes"].append(f"- Attempt {t['attempts']} ({builder}): the checks failed; output in {out}")
            if t["attempts"] < WORKER_ATTEMPTS and end not in ("timeout", "gone", "not delivered"):
                log(f"{tid}: checks failed; asking {builder} to fix it")
                continue
            ans = ask_human(session, f"aidev_test: {tid} failed its checks {t['attempts']}x in {builder}. Next?",
                            escalation_options(run, builder),
                            detail=f"Last check output: {out}. To steer the builder, type into the {builder} pane "
                            f"(workspace {WS[builder]}) first, then answer retry.")
            run.event("decision", task=tid, answer=ans)
            if ans == "retry":
                t["attempts"] = 0
                continue
            if ans.startswith("escalate"):
                builder = run.data["builder"] = "build-pickle" if "pickle" in ans else "build-claude"
                ensure_builder(run, session, cfg, builder)
                t["attempts"] = 0
                continue
            if ans == "skip":
                t["status"] = "skipped"
                run.save()
                break
            run.data["phase"] = "aborted"
            run.save()
            return
    run.data["phase"] = "review"
    run.save()


def phase_review(run, session, cfg, ralph):
    wd = run.data["work_dir"]
    report = os.path.join(run.state, "reviews", f"{run.id}.md")
    rounds = run.data.setdefault("review_rounds", 0)
    if os.path.exists(report):
        os.replace(report, report + f".{int(time.time())}")
    if not window_named(session, "review"):
        system = prompt_text("review", WORK_DIR=wd, PLAN_DIR=run.plan_dir, REPORT=report,
                             CHECKS=os.path.join(run.dir, "tasks"))
        first = (f"Review the uncommitted changes in {wd} against the plan in {run.plan_dir}/PLAN.txt. Write the "
                 f"report to {report}.")
        open_pane(run, session, "review", write_script(run, "review", claude_body(run, cfg, "review", system, first,
                                                                                  wd)), wd)
        name_ws(session, "review")
    else:
        queue(session, "review", f"The builder changed the work. Review the changes in {wd} again and write a new "
              f"report to {report}.")
    tell_human(session, "review started", f"Workspace {WS['review']}: Claude reviews; report {report}.")
    log("review: waiting for the report")
    while not (os.path.exists(report) and agent_state(session, "review") in AT_REST + ("none",)):
        if agent_state(session, "review") == "gone":
            break
        time.sleep(5)
    try:
        verdict = open(report).readline().strip()
    except OSError:
        verdict = ""
    run.event("review", verdict=verdict, report=report)
    if verdict == "Verdict: PASS":
        run.data["phase"] = "done"
        run.save()
        return
    ans = ask_human(session, f"aidev_test: review says {verdict or 'nothing (no report)'}. Next?",
                    ["rework", "accept", "abort"], detail=f"The report: {report}")
    run.event("decision", task="review", answer=ans)
    if ans == "accept":
        run.data["phase"] = "done"
    elif ans == "rework":
        builder = run.data.get("builder") or "build"
        queue(session, builder, f"aidev_test review: the review in {report} found problems. Fix every finding, run "
              "the checks of the tasks you touch, then stop.")
        wait_turn(session, builder)
        prd, verify, _h = ralph.load_plan(run.project)
        for tid in task_order(prd):
            if run.data["tasks"].get(tid, {}).get("status") != "verified":
                continue
            ok, _ = run_verify(verify[tid], wd, os.path.join(run.dir, "tasks", f"{tid}-reverify-{rounds + 1}.txt"))
            if not ok:
                log(f"{tid} no longer verifies after the rework")
                run.data["tasks"][tid].update(status="pending", attempts=0)
                run.data["phase"] = "build"
        run.data["review_rounds"] = rounds + 1
    else:
        run.data["phase"] = "aborted"
    run.save()


def driver(project):
    global LOG_PATH
    ralph = load_ralph()
    os.environ["RALPH_MCP_ROOTS"] = project
    run = Run(project)
    os.makedirs(run.dir, exist_ok=True)
    LOG_PATH = os.path.join(run.dir, "driver.log")
    session = run.data.get("session") or session_name(project)
    WS.update(run.data.get("ws") or {})
    cfg = pane_configs(project)
    log(f"aidev_test driver: run {run.id}, session {session}, phase {run.data['phase']}, state {run.state}")
    if run.data.get("work_dir"):
        start_dev_workspace(run, session)
    while True:
        phase = run.data["phase"]
        if phase == "research":
            phase_research(run, session, cfg)
        elif phase == "plan":
            if not window_named(session, "plan"):
                start_plan_pane(run, session, cfg, f"Carry on with the plan in {run.plan_dir}.")
            phase_plan(run, session, cfg, ralph)
        elif phase == "build":
            phase_build(run, session, cfg, ralph)
        elif phase == "review":
            phase_review(run, session, cfg, ralph)
        else:
            break
    wd = run.data.get("work_dir") or project
    msg = (f"Run {run.id} done. Changes are uncommitted in {wd}; commit with gpa when you are happy."
           if run.data["phase"] == "done" else f"Run {run.id} {run.data['phase']}.")
    log(msg)
    tell_human(session, f"aidev_test {run.data['phase']}", msg)
    return 0


# ---- entry points ---------------------------------------------------------------------------------------------
def preflight(need_local=True):
    problems = [f"{t} is not installed" for t in ("tuios", "claude", "pi", "git", "gh") if not shutil.which(t)]
    if not os.path.isfile(os.path.join(AISTACK, "ralph_mcp.py")):
        problems.append(f"{AISTACK}/ralph_mcp.py is missing (run darwin-rebuild)")
    if need_local:
        import urllib.request
        try:
            urllib.request.urlopen(LOCAL_ENDPOINT + "/v1/models", timeout=5).read()
        except (OSError, ValueError):
            problems.append(f"the local model is not answering at {LOCAL_ENDPOINT} (start it: sudo launchctl "
                            "kickstart -k system/org.nixos.llama-server-local), or use --no-research")
    return problems


def new_session(session, cwd):
    """A detached session with no windows of its own (tuios new opens one shell; the layers bring their own)."""
    code, _o, err = tuios("new", session, "-d", "--cwd", cwd)
    if code:
        return err.strip() or "tuios new failed"
    for w in windows(session):
        tuios("close-window", w["window_id"], "-s", session)
    return None


def cmd_start(argv):
    resume = "--resume" in argv
    no_research = "--no-research" in argv
    task = " ".join(a for a in argv if a not in ("--resume", "--no-research")).strip()
    if nested_in_herdr():
        print("aidev_test: run it from a plain Ghostty window, not inside herdr (no nested multiplexers).",
              file=sys.stderr)
        return 1
    project = project_root(os.getcwd())
    # --resume goes back to the session the run was started in; a new run opens in this one (start_session)
    session = (Run(project).data.get("session") if resume else None) or start_session(project)
    own = session == session_name(project)
    driver_w = None if own else window_named(session, "driver")
    if driver_w and os.path.realpath(driver_w.get("cwd") or "") != project:
        print(f"aidev_test: {session} already holds a run for {driver_w.get('cwd')}; one run per session. Use "
              "AIDEV_TEST_OWN_SESSION=1 for a session of its own.", file=sys.stderr)
        return 1
    running = session_exists(session) if own else bool(driver_w)
    if running and not resume:
        if task:
            print(f"aidev_test: a run is already open in {session}. Type the task into the research or plan pane.",
                  file=sys.stderr)
        return attach(session)
    problems = preflight(need_local=not no_research and not resume)
    if problems:
        print("aidev_test: " + "; ".join(problems), file=sys.stderr)
        return 1
    run = Run(project, None if resume else time.strftime("%Y%m%d-%H%M%S"))
    if resume and not os.path.exists(run.path):
        print("aidev_test --resume: no unfinished run in this project.", file=sys.stderr)
        return 1
    os.makedirs(run.dir, exist_ok=True)
    run.data["session"] = session
    err = assign_workspaces(run, session, own)
    if err:
        print(f"aidev_test: {err}", file=sys.stderr)
        return 1
    run.save()  # before the driver pane opens: the driver reads the session and workspaces from it
    cfg = pane_configs(project)
    if own and not running:
        err = new_session(session, project)
        if err:
            print(f"aidev_test: {err}", file=sys.stderr)
            return 1
    if not window_named(session, "driver"):
        run.data["panes"].pop("driver", None)
    # the AIDEV_TEST_* settings of this shell reach the driver even when the daemon was started elsewhere
    passthru = "".join(f"export {k}={shlex.quote(v)}\n" for k, v in sorted(os.environ.items())
                       if k.startswith("AIDEV_TEST_") and k not in ("AIDEV_TEST_NO_ATTACH", "AIDEV_TEST_ALLOW_NESTED"))
    dscript = write_script(run, "driver", f"{passthru}cd {shlex.quote(project)}\n{shlex.quote(sys.executable)} "
                           f"{shlex.quote(os.path.realpath(__file__))} driver {shlex.quote(project)}")
    open_pane(run, session, "driver", dscript, project, grants="read,write,admin")
    name_ws(session, "driver")
    if run.data["phase"] == "research" and not resume:
        if no_research:
            start_plan_pane(run, session, cfg, task or "Wait for the person to describe the work.")
            tuios("select-workspace", str(WS["plan"]), "-s", session)
        else:
            open_pane(run, session, "research", write_script(run, "research", research_body(run, cfg, task)),
                      project)
            name_ws(session, "research")
            tuios("select-workspace", str(WS["research"]), "-s", session)
    else:  # resume: the layers that were open come back with their conversations (their launchers --resume); the
        # driver reopens the builder itself, with a fresh launcher, when the build phase needs it
        for name in ("research", "plan", "review"):
            p = run.data["panes"].get(name) or {}
            if p.get("script") and os.path.exists(p["script"]) and not window_named(session, name):
                tuios("new-window", name, "-s", session, "--workspace", str(WS[name]), "--cwd",
                      p.get("cwd", project), "--grants", p.get("grants", "read"), "--no-focus", "--", "/bin/zsh",
                      p["script"])
                name_ws(session, name)
    run.save()
    return attach(session)


def cmd_ai(argv):
    cont = "-c" in argv
    msg = " ".join(a for a in argv if a != "-c").strip()
    if nested_in_herdr():
        print("ai_test: run it from a plain Ghostty window, not inside herdr.", file=sys.stderr)
        return 1
    cwd = os.path.realpath(os.getcwd())
    session = "ai_test-" + safe_name(os.path.basename(cwd))
    if session_exists(session) and not msg and not cont:
        return attach(session)
    cfg = pane_configs(cwd)
    sessions_p = os.path.join(TEST_HOME, "ai", "sessions.json")
    known = rj(sessions_p, {})
    sid = known.get(cwd) if cont else None
    argv_c = ["claude", "--settings", cfg["claude_settings"], "--mcp-config", cfg["claude_mcp"], "-n", "ai_test"]
    if sid:
        argv_c += ["--resume", sid]
    else:
        sid = known[cwd] = str(uuid.uuid4())
        wj(sessions_p, known)
        argv_c += ["--session-id", sid]
    if msg:
        argv_c.append(msg)
    if not session_exists(session):
        err = new_session(session, cwd)
        if err:
            print(f"ai_test: {err}", file=sys.stderr)
            return 1
    tuios("new-window", f"claude-{sid[:8]}", "-s", session, "--cwd", cwd, "--grants", "read", "--",
          "/bin/zsh", "-c", " ".join(map(shlex.quote, argv_c)) + "; exec zsh -i")
    return attach(session)


def cmd_status(argv):
    project = project_root(argv[0] if argv else os.getcwd())
    run = Run(project)
    if not os.path.exists(run.path):
        print("no unfinished aidev_test run in this project")
        return 1
    d = run.data
    print(f"run {run.id}: phase {d['phase']}, work dir {d.get('work_dir') or '-'}")
    for tid, t in d.get("tasks", {}).items():
        print(f"  {tid}: {t['status']} ({t['attempts']} attempt(s))")
    print(f"state: {run.dir}")
    return 0


def main(argv):
    cmd, rest = (argv[0], argv[1:]) if argv else ("", [])
    if cmd == "start":
        return cmd_start(rest)
    if cmd == "driver" and rest:
        return driver(os.path.realpath(rest[0]))
    if cmd == "ai":
        return cmd_ai(rest)
    if cmd == "status":
        return cmd_status(rest)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
