#!/usr/bin/env python3
"""ainfo bridge: an MCP server (stdio, JSON-RPC 2.0) that lets the local model in pi relay between Claude and Lumo.

pi (Qwen) has exactly these tools and no file, shell or edit tools of its own:
  ainfo_investigate(question)   Claude researches (MCP servers + local reads), Lumo looks up online docs, Claude writes
                               the advice. Runs as a background job; the bridge does the hand-offs.
  ainfo_ask_claude(request)     one Claude call, when the user asks Claude something directly
  ainfo_ask_lumo(question)      one Lumo call, when the user asks Lumo something directly
  ainfo_wait(job_id)            news from a job (what Claude is reading, what Lumo was asked) and the final result

Read-only is enforced here, not in prompts: Claude runs with ainfo_guard.py as a PreToolUse hook (`--settings`),
`--disallowedTools` for every writing built-in, and inside a macOS sandbox that refuses file writes outside a few
cache directories. Lumo has no tools at all. State (Claude session id, Lumo history, event log, advice files) lives in
AINFO_STATE_DIR (~/.ainfo/<project key>), never in a repository, so a crashed pi session can be resumed.
"""

import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
PROJECT = os.path.realpath(os.environ.get("AINFO_PROJECT") or os.getcwd())
STATE_DIR = os.environ.get("AINFO_STATE_DIR") or os.path.expanduser("~/.ainfo/default")
AISTACK_DIR = os.environ.get("AINFO_AISTACK_DIR") or os.path.expanduser(
    "~/.config/aistack"
)
CLAUDE_BIN = os.environ.get("AINFO_CLAUDE_BIN", "claude")
CLAUDE_MODEL = os.environ.get("AINFO_CLAUDE_MODEL") or os.environ.get(
    "AISTACK_CLAUDE_MODEL", "sonnet"
)
CLAUDE_EFFORT = os.environ.get("AINFO_CLAUDE_EFFORT") or os.environ.get(
    "AISTACK_CLAUDE_EFFORT", "medium"
)
CLAUDE_BUDGET = os.environ.get("AINFO_CLAUDE_BUDGET_USD", "2.0")  # per Claude call
CLAUDE_TIMEOUT_S = int(os.environ.get("AINFO_CLAUDE_TIMEOUT_S", "900"))
LUMO_TIMEOUT_S = int(os.environ.get("AINFO_LUMO_TIMEOUT_S", "300"))
MAX_CLAUDE = int(os.environ.get("AINFO_MAX_CLAUDE_CALLS", "3"))  # per ainfo_investigate
MAX_LUMO = int(os.environ.get("AINFO_MAX_LUMO_CALLS", "2"))  # per ainfo_investigate
SANDBOX = os.environ.get("AINFO_SANDBOX", "on") != "off"
WAIT_S = 25
PROTOCOL = "2024-11-05"


def read_text(name, default):
    try:
        with open(os.path.join(HERE, name)) as f:
            return f.read()
    except OSError:
        return default


CLAUDE_SYSTEM = read_text("claude-system.md", "")
LUMO_PROMPT = read_text("lumo-prompt.md", "{questions}")

JOBS = {}
LOCK = threading.Lock()
STATE_LOCK = threading.Lock()


# ---- state ------------------------------------------------------------------------------------------------------
def state_path():
    return os.path.join(STATE_DIR, "state.json")


def load_state():
    try:
        return json.load(open(state_path()))
    except (OSError, ValueError):
        return {
            "claude_session": "",
            "lumo_history": [],
            "cost_usd": 0.0,
            "claude_calls": 0,
            "lumo_calls": 0,
            "advice_n": 0,
        }


def save_state(st):
    with STATE_LOCK:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = state_path() + ".tmp"
        with open(tmp, "w") as f:
            json.dump(st, f, indent=1)
        os.replace(tmp, state_path())


def log_event(job, kind, text):
    ev = {"t": time.strftime("%H:%M:%S"), "who": kind, "text": redact(text)[:600]}
    with LOCK:
        job["events"].append(ev)
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, "events.jsonl"), "a") as f:
            f.write(json.dumps({"job": job["id"], **ev}) + "\n")
    except OSError:
        pass


# ---- redaction (everything that goes to Lumo) ---------------------------------------------------------------------
REDACTIONS = [
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"
        ),
        "[REDACTED PRIVATE KEY]",
    ),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED TOKEN]"),
    (re.compile(r"\bxox[baprs]-[\w-]{10,}"), "[REDACTED TOKEN]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED AWS KEY]"),
    (
        re.compile(r"\bdp\.(?:st|pt|sa|ct|scim)\.[\w.-]{20,}"),
        "[REDACTED DOPPLER TOKEN]",
    ),
    (re.compile(r"\beyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]*"), "[REDACTED JWT]"),
    (re.compile(r"(?i)\bBearer\s+[\w.~+/=-]{16,}"), "Bearer [REDACTED]"),
    (
        re.compile(
            r"(?i)((?:token|secret|passw(?:or)?d|api[_-]?key|authorization|private[_-]?key)[\"']?\s*[:=]\s*[\"']?)([^\s\"',;}{]{6,})"
        ),
        r"\1[REDACTED]",
    ),
    (re.compile(r"\b[A-Fa-f0-9]{40,}\b"), "[REDACTED HEX]"),
]


def redact(text):
    for rx, rep in REDACTIONS:
        text = rx.sub(rep, text)
    extra = os.environ.get("AINFO_REDACT_EXTRA")
    if extra:
        text = re.sub(extra, "[REDACTED]", text)
    return text


URL_RE = re.compile(r"https?://[^\s<>\"'`\])}]+")


def urls_in(text):
    return {u.rstrip(".,;:!?*") for u in URL_RE.findall(text or "")}


# ---- Claude -----------------------------------------------------------------------------------------------------
DISALLOWED = [
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
    "Agent",
    "Task",
    "Skill",
]


def sandbox_profile():
    h = os.path.expanduser("~")
    sub = lambda p: f'(subpath "{p}")'
    allow = [
        sub(p)
        for p in (
            "/private/tmp",
            "/private/var/folders",
            "/private/var/tmp",
            f"{h}/.claude",
            f"{h}/.claude-global",
            f"{h}/.cache",
            f"{h}/.npm",
            f"{h}/.local",
            f"{h}/.ainfo",
            f"{h}/.bun",
            f"{h}/.token-optimizer",
            f"{h}/Library/Caches",
            f"{h}/.config/claude",
            f"{h}/.config/configstore",
            f"{h}/.docker",
            f"{h}/.cargo",
            f"{h}/.rustup",
            f"{h}/.pi",
            f"{h}/.aws/sso/cache",  # aws CLI refreshes the SSO token and caches role credentials here
            f"{h}/.aws/cli/cache",
        )
    ]
    extra = [sub(p) for p in os.environ.get("AINFO_SANDBOX_WRITE", "").split(":") if p]
    prof = (
        "(version 1)\n(allow default)\n(deny file-write*)\n"
        '(allow file-write* (literal "/dev/null") (literal "/dev/tty") (literal "/dev/dtracehelper") (regex #"^/dev/(tty|pty|fd/)"))\n'
        f"(allow file-write* {' '.join(allow + extra)})\n"
        f'(allow file-write* (regex #"^{re.escape(h)}/\\.claude\\.json"))\n'
    )
    path = os.path.join(STATE_DIR, "sandbox.sb")
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write(prof)
    return path


def settings_file():
    path = os.path.join(STATE_DIR, "claude-settings.json")
    guard = os.path.join(HERE, "ainfo_guard.py")
    cfg = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": ".*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{sys.executable} {guard}",
                            "timeout": 10,
                        }
                    ],
                }
            ]
        }
    }
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f)
    return path


def brief(tool, tin):
    """One short line about a Claude tool call, for the news the local model relays."""
    if tool == "Bash":
        return "runs: " + str(tin.get("command", ""))[:160]
    if tool in ("Read", "Grep", "Glob", "LS"):
        return (
            f"{tool}: "
            + str(tin.get("file_path") or tin.get("pattern") or tin.get("path") or "")[
                :160
            ]
        )
    short = tool.replace("mcp__", "").replace("__", ": ")
    args = (
        ", ".join(f"{k}={str(v)[:50]}" for k, v in list(tin.items())[:3])
        if isinstance(tin, dict)
        else ""
    )
    return f"{short}({args})"[:200]


def tool_result_text(block):
    c = block.get("content")
    if isinstance(c, list):
        return "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
    return str(c or "")


def run_claude(job, prompt, st):
    """One Claude call. Returns dict(text, cost, session, error, seen_urls, denied)."""
    cmd = [CLAUDE_BIN, "-p", "--output-format", "stream-json", "--verbose", "--model", CLAUDE_MODEL, "--effort", CLAUDE_EFFORT,
           "--max-budget-usd", str(CLAUDE_BUDGET), "--settings", settings_file(), "--permission-prompts", "none",
           "--disallowedTools", *DISALLOWED, "--append-system-prompt", CLAUDE_SYSTEM]  # fmt: skip
    if st.get("claude_session"):
        cmd += ["--resume", st["claude_session"]]
    if SANDBOX and shutil.which("sandbox-exec"):
        cmd = ["sandbox-exec", "-f", sandbox_profile()] + cmd
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    p = subprocess.Popen(
        cmd,
        cwd=PROJECT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=True,
    )
    job["procs"].append(p)
    killer = threading.Timer(
        CLAUDE_TIMEOUT_S,
        lambda: os.killpg(p.pid, signal.SIGTERM) if p.poll() is None else None,
    )
    killer.start()
    out = {
        "text": "",
        "cost": 0.0,
        "session": st.get("claude_session", ""),
        "error": "",
        "seen_urls": set(),
        "denied": [],
    }
    stderr_buf = []
    threading.Thread(
        target=lambda: stderr_buf.append(p.stderr.read()), daemon=True
    ).start()
    try:
        p.stdin.write(prompt)
        p.stdin.close()
        texts, tool_names = [], {}
        for line in p.stdout:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = d.get("type")
            if t == "system" and d.get("subtype") == "init":
                bad = [
                    m.get("name")
                    for m in d.get("mcp_servers", [])
                    if m.get("status") not in ("connected", "pending")
                ]
                if bad and not job.get("warned_mcp"):
                    job["warned_mcp"] = True
                    log_event(
                        job,
                        "claude",
                        "MCP servers not connected: " + ", ".join(map(str, bad)),
                    )
            elif t == "assistant":
                for b in d.get("message", {}).get("content", []) or []:
                    if b.get("type") == "tool_use":
                        tool_names[b.get("id")] = b.get("name")
                        log_event(
                            job,
                            "claude",
                            brief(b.get("name", ""), b.get("input") or {}),
                        )
                    elif b.get("type") == "text" and b.get("text", "").strip():
                        texts.append(b["text"])
            elif t == "user":
                for b in (
                    (d.get("message", {}).get("content") or [])
                    if isinstance(d.get("message", {}).get("content"), list)
                    else []
                ):
                    if b.get("type") == "tool_result":
                        txt = tool_result_text(b)
                        out["seen_urls"] |= urls_in(txt)
                        if b.get("is_error") and "ainfo is read-only" in txt:
                            out["denied"].append(
                                f"{tool_names.get(b.get('tool_use_id'), '?')}: {txt[:140]}"
                            )
                            log_event(job, "guard", "blocked " + out["denied"][-1])
            elif t == "result":
                out["cost"] = float(d.get("total_cost_usd") or 0)
                out["session"] = d.get("session_id") or out["session"]
                if d.get("is_error"):
                    out["error"] = str(d.get("result") or d.get("subtype") or "error")[
                        :400
                    ]
                out["text"] = str(d.get("result") or "") or "\n".join(texts[-1:])
        p.wait(timeout=30)
    finally:
        killer.cancel()
    if not out["text"] and not out["error"]:
        out["error"] = (
            "claude exited without a result: "
            + (stderr_buf[0] if stderr_buf else "")[-300:]
        ).strip()
    return out


JSON_BLOCK = re.compile(r"```json\s*(\{[\s\S]*?\})\s*```\s*$")


def split_contract(text):
    """(prose, contract dict) from Claude's reply; the contract is the trailing ```json block."""
    m = JSON_BLOCK.search(text.rstrip())
    if not m:
        return text.strip(), {}
    try:
        return text[: m.start()].strip(), json.loads(m.group(1))
    except ValueError:
        return text[: m.start()].strip(), {}


# ---- Lumo -------------------------------------------------------------------------------------------------------
def load_ralph():
    spec = importlib.util.spec_from_file_location(
        "ralph_mcp", os.path.join(AISTACK_DIR, "ralph_mcp.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lumo_available():
    try:
        return next(iter(load_ralph().tamer_endpoints()), None) is not None
    except Exception:  # noqa: BLE001
        return False


def run_lumo(job, questions_text, st):
    """One Lumo call (web research through lumo-tamer). Returns (reply text, error)."""
    prompt = LUMO_PROMPT.replace("{questions}", redact(questions_text))
    messages = []
    for h in st.get("lumo_history", [])[-4:]:
        messages.append({"role": h["role"], "content": h["content"][:6000]})
    messages.append({"role": "user", "content": prompt})
    errors = []
    try:
        endpoints = load_ralph().tamer_endpoints()
    except Exception as e:  # noqa: BLE001
        return "", f"cannot find the tamer helpers in {AISTACK_DIR} ({e})"
    for base, key in endpoints:
        log_event(job, "lumo", f"researching online via {base}")
        req = urllib.request.Request(
            base.rstrip("/") + "/chat/completions",
            data=json.dumps(
                {
                    "model": os.environ.get("AINFO_LUMO_MODEL", "lumo"),
                    "messages": messages,
                }
            ).encode(),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {key}"} if key else {}),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=LUMO_TIMEOUT_S) as r:
                reply = json.load(r)["choices"][0]["message"].get("content") or ""
        except Exception as e:  # noqa: BLE001
            errors.append(f"{base}: {type(e).__name__}: {e}")
            if "timed out" in str(e).lower():
                break
            continue
        st.setdefault("lumo_history", []).extend(
            [
                {"role": "user", "content": prompt[:6000]},
                {"role": "assistant", "content": reply},
            ]
        )
        st["lumo_history"] = st["lumo_history"][-8:]
        return reply, ""
    return "", "; ".join(errors) or "no Lumo (lumo-tamer) answered"


# ---- the investigation loop ---------------------------------------------------------------------------------------
FIRST = """QUESTION FROM THE USER (they act on your advice themselves; you and everyone else here are read-only):
{question}

Working directory: {cwd}. Research with your MCP servers and read-only local tools. When you need documentation, a manpage,
a vendor guide or a best practice, do NOT look it up yourself: list it in lumo_lookups and Lumo will search the web for you.
This is round {n} of at most {max_claude}."""

AFTER_LUMO = """LUMO'S ONLINE RESEARCH (answers to your lumo_lookups; the URLs here are the only web sources you may cite):
{lumo}

Continue. If this is enough, write the final advice now (final=true). If a lookup failed or a new one is needed and rounds remain,
list it in lumo_lookups (final=false). This is round {n} of at most {max_claude}."""

LUMO_DOWN = "Lumo (online research) is not available. Say so in the advice, label every claim that needs documentation as UNVERIFIED, and finish now (final=true)."
LAST_ROUND = "This is the last round: write the final advice now (final=true) and mark anything unverified."


def check_sources(advice, lumo_urls, claude_urls):
    cited = urls_in(advice)
    good = sorted(u for u in cited if u in lumo_urls or u in claude_urls)
    bad = sorted(cited - set(good))
    return {"verified": good, "unverified": bad}


def investigate(job, question, context):
    st = load_state()
    claude_urls, lumo_urls, lookups_log = set(), set(), []
    prompt = FIRST.format(
        question=(
            question + ("\n\nEXTRA CONTEXT:\n" + context if context else "")
        ).strip(),
        cwd=PROJECT,
        n=1,
        max_claude=MAX_CLAUDE,
    )
    lumo_calls, claude_calls, cost = 0, 0, 0.0
    lumo_ok = lumo_available()
    if not lumo_ok:
        prompt += "\n\n" + LUMO_DOWN
    prose, contract = "", {}
    while True:
        claude_calls += 1
        log_event(
            job,
            "stack",
            f"Claude round {claude_calls}/{MAX_CLAUDE}: {'researching' if claude_calls == 1 else 'reading Lumo findings'}",
        )
        r = run_claude(job, prompt, st)
        cost += r["cost"]
        claude_urls |= r["seen_urls"]
        st["claude_session"], st["cost_usd"] = (
            r["session"],
            round(st.get("cost_usd", 0) + r["cost"], 4),
        )
        st["claude_calls"] = st.get("claude_calls", 0) + 1
        save_state(st)
        if r["error"]:
            log_event(job, "stack", "Claude problem: " + r["error"])
            if not prose:
                return {"ok": False, "problem": r["error"], "cost_usd": round(cost, 3)}
            break
        prose, contract = split_contract(r["text"])
        asks = [
            a
            for a in (contract.get("lumo_lookups") or [])
            if isinstance(a, dict) and a.get("question")
        ]
        log_event(
            job,
            "claude",
            f"round {claude_calls} done (${r['cost']:.2f}); asks Lumo {len(asks)} thing(s)"
            if asks
            else f"round {claude_calls} done (${r['cost']:.2f}); no more lookups",
        )
        if (
            not asks
            or contract.get("final") is True
            or claude_calls >= MAX_CLAUDE
            or lumo_calls >= MAX_LUMO
            or not lumo_ok
        ):
            break
        for a in asks:
            log_event(job, "claude->lumo", f"{a.get('id', '?')}: {a['question']}"[:300])
        qtext = "\n".join(
            f"{a.get('id', f'L{i + 1}')}. {a['question']}"
            + (f"\n   why it matters: {a['why']}" if a.get("why") else "")
            for i, a in enumerate(asks)
        )
        if prose:
            qtext = (
                "Findings so far from the local investigation (for context):\n"
                + prose[:3000]
                + "\n\nQUESTIONS:\n"
                + qtext
            )
        lumo_calls += 1
        reply, err = run_lumo(job, qtext, st)
        st["lumo_calls"] = st.get("lumo_calls", 0) + 1
        save_state(st)
        if err:
            log_event(job, "stack", "Lumo problem: " + err[:300])
            lumo_ok = False
            prompt = LUMO_DOWN
            continue
        lumo_urls |= urls_in(reply)
        lookups_log.append(
            {"asked": [a["question"] for a in asks], "reply_chars": len(reply)}
        )
        log_event(
            job,
            "lumo->claude",
            f"{len(urls_in(reply))} link(s), {len(reply)} chars returned",
        )
        prompt = AFTER_LUMO.format(
            lumo=reply, n=claude_calls + 1, max_claude=MAX_CLAUDE
        )
        if claude_calls + 1 >= MAX_CLAUDE:
            prompt += "\n" + LAST_ROUND
    prose = redact(
        prose
    )  # Claude may read secrets to authenticate; none belongs in the advice
    st["advice_n"] = st.get("advice_n", 0) + 1
    save_state(st)
    path = os.path.join(STATE_DIR, f"advice-{st['advice_n']:03d}.md")
    srcs = check_sources(prose, lumo_urls, claude_urls)
    try:
        with open(path, "w") as f:
            f.write(f"# {question[:200]}\n\n{prose}\n")
    except OSError:
        path = ""
    out = {
        "ok": True,
        "advice": prose,
        "source_check": srcs,
        "need_from_user": contract.get("need_from_user") or [],
        "calls": {"claude": claude_calls, "lumo": lumo_calls},
        "cost_usd": round(cost, 3),
        "session_total_usd": st["cost_usd"],
        "saved_to": path,
    }
    if not lumo_ok:
        out["warning"] = (
            "Lumo was not available: the advice has no online documentation behind it"
        )
    if srcs["unverified"]:
        out["warning"] = (
            out.get("warning", "")
            + " URLs in the advice that no tool or Lumo returned: they may be invented; do not trust them"
        ).strip()
    return out


def single_claude(job, request):
    st = load_state()
    r = run_claude(job, request, st)
    st["claude_session"], st["cost_usd"] = (
        r["session"],
        round(st.get("cost_usd", 0) + r["cost"], 4),
    )
    save_state(st)
    if r["error"]:
        return {"ok": False, "problem": r["error"]}
    prose, _ = split_contract(r["text"])
    return {"ok": True, "claude": prose, "cost_usd": round(r["cost"], 3)}


def single_lumo(job, question):
    st = load_state()
    reply, err = run_lumo(job, question, st)
    save_state(st)
    return (
        {"ok": False, "problem": err}
        if err
        else {"ok": True, "lumo": reply, "links": sorted(urls_in(reply))}
    )


# ---- jobs -------------------------------------------------------------------------------------------------------
def start_job(kind, fn, *args):
    jid = f"{kind}-{int(time.time())}"
    job = {
        "id": jid,
        "kind": kind,
        "events": [],
        "cursor": 0,
        "done": False,
        "result": None,
        "procs": [],
        "started": time.time(),
    }
    with LOCK:
        JOBS[jid] = job

    def runner():
        try:
            job["result"] = fn(job, *args)
        except Exception as e:  # noqa: BLE001
            job["result"] = {"ok": False, "problem": f"{type(e).__name__}: {e}"}
        job["done"] = True
        log_event(job, "stack", "finished")

    threading.Thread(target=runner, daemon=True).start()
    return job


def tool_investigate(a):
    q = str(a.get("question") or "").strip()
    if not q:
        return {"ok": False, "problem": "question is empty"}
    job = start_job("investigate", investigate, q, str(a.get("context") or ""))
    return {
        "ok": True,
        "job_id": job["id"],
        "next": "call ainfo_wait with this job_id and report each event to the user",
    }


def tool_ask_claude(a):
    q = str(a.get("request") or "").strip()
    return (
        {"ok": False, "problem": "request is empty"}
        if not q
        else {
            "ok": True,
            "job_id": start_job("claude", single_claude, q)["id"],
            "next": "call ainfo_wait",
        }
    )


def tool_ask_lumo(a):
    q = str(a.get("question") or "").strip()
    return (
        {"ok": False, "problem": "question is empty"}
        if not q
        else {
            "ok": True,
            "job_id": start_job("lumo", single_lumo, q)["id"],
            "next": "call ainfo_wait",
        }
    )


def tool_wait(a):
    job = JOBS.get(str(a.get("job_id") or ""))
    if not job:
        return {
            "ok": False,
            "problem": "unknown job_id; jobs from before pi restarted are gone: ask the question again (Claude and Lumo keep their context)",
        }
    end = time.time() + WAIT_S
    while (
        time.time() < end and not job["done"] and len(job["events"]) - job["cursor"] < 8
    ):
        time.sleep(0.5)
    with LOCK:
        new = job["events"][job["cursor"] :]
        job["cursor"] = len(job["events"])
    out = {
        "job_id": job["id"],
        "done": job["done"],
        "elapsed_s": int(time.time() - job["started"]),
        "events": [f"{e['t']} [{e['who']}] {e['text']}" for e in new],
    }
    if job["done"]:
        out["result"] = job["result"]
    else:
        out["next"] = "report these events to the user, then call ainfo_wait again"
    return out


def tool_cancel(a):
    job = JOBS.get(str(a.get("job_id") or ""))
    if not job:
        return {"ok": False, "problem": "unknown job_id"}
    for p in job["procs"]:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
    return {"ok": True, "cancelled": job["id"]}


S = lambda props, req: {"type": "object", "properties": props, "required": req}
STR = {"type": "string"}
TOOLS = {
    "ainfo_investigate": (
        tool_investigate,
        "Start the full investigation of a question, error or URL: Claude researches with its MCP servers and local reads, Lumo looks up online documentation, Claude writes the advice. Returns a job_id: call ainfo_wait.",
        S({"question": STR, "context": STR}, ["question"]),
    ),
    "ainfo_ask_claude": (
        tool_ask_claude,
        "Relay one request to Claude only (MCP and local read-only research). Returns a job_id: call ainfo_wait.",
        S({"request": STR}, ["request"]),
    ),
    "ainfo_ask_lumo": (
        tool_ask_lumo,
        "Relay one question to Lumo only (online documentation and best-practice search). Returns a job_id: call ainfo_wait.",
        S({"question": STR}, ["question"]),
    ),
    "ainfo_wait": (
        tool_wait,
        "News from a job: what Claude is looking at and what is passed between Claude and Lumo, plus the final result when done. Waits up to 25 s.",
        S({"job_id": STR}, ["job_id"]),
    ),
    "ainfo_cancel": (
        tool_cancel,
        "Stop a running job.",
        S({"job_id": STR}, ["job_id"]),
    ),
}


def handle(req):
    m = req.get("method")
    if m == "initialize":
        return {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "ainfo", "version": "0.1.0"},
        }
    if m == "ping":
        return {}
    if m == "tools/list":
        return {
            "tools": [
                {"name": n, "description": d, "inputSchema": s}
                for n, (_, d, s) in TOOLS.items()
            ]
        }
    if m == "tools/call":
        p = req.get("params", {})
        fn = TOOLS.get(p.get("name"))
        if not fn:
            return {
                "content": [{"type": "text", "text": f"unknown tool {p.get('name')}"}],
                "isError": True,
            }
        try:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(fn[0](p.get("arguments") or {}), indent=1),
                    }
                ]
            }
        except Exception as e:  # noqa: BLE001
            return {
                "content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
                "isError": True,
            }
    return None


def main():
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except ValueError:
            continue
        if "id" not in req:
            continue
        try:
            res = handle(req)
            msg = (
                {"jsonrpc": "2.0", "id": req["id"], "result": res}
                if res is not None
                else {
                    "jsonrpc": "2.0",
                    "id": req["id"],
                    "error": {"code": -32601, "message": "method not found"},
                }
            )
        except Exception as e:  # noqa: BLE001
            msg = {
                "jsonrpc": "2.0",
                "id": req["id"],
                "error": {"code": -32603, "message": str(e)},
            }
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


def cli(question):
    """Headless run without pi (tests, debugging): prints the events as they happen, then the result."""
    job = start_job("investigate", investigate, question, "")
    seen = 0
    while not job["done"]:
        time.sleep(0.5)
        for e in job["events"][seen:]:
            print(f"{e['t']} [{e['who']}] {e['text']}", flush=True)
        seen = len(job["events"])
    for e in job["events"][seen:]:
        print(f"{e['t']} [{e['who']}] {e['text']}")
    print(json.dumps(job["result"], indent=1))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--cli":
        cli(" ".join(sys.argv[2:]))
    else:
        main()
