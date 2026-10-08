#!/usr/bin/env python3
"""MCP bridge (stdio, JSON-RPC 2.0) between a chat agent (pi) and the aistack run driver.

Tools: ralph_validate_plan, ralph_plan (Claude writes the plan), ralph_update_task, repo_tree / repo_read / repo_grep (aidev: budgeted research), ralph_run, ralph_status, ralph_respond, ralph_cancel, ralph_runs, lumo_consult (tier 0).
Runs are detached processes (ralph_driver.py); tool calls return quickly, and ralph_status can wait up to
45s for news so the chat agent can follow a run without a tight loop (MCP clients time out near 60s).

Nothing aistack-related is written into the repository: plan files, runs, questions, reviews and Ralph's own
state live in the state dir (AISTACK_STATE_DIR, ~/.aistack/<project key>). When the launcher found a main
checkout (AISTACK_WORKTREE_MODE=create), the git worktree + draft PR is created by ralph_run, after the user has
confirmed the plan; the agents then work there.

Safety: only works inside RALPH_MCP_ROOTS (colon-separated); agent names come from the environment the
launcher sets (AISTACK_WORKER_AGENT / AISTACK_FALLBACK_AGENT / AISTACK_REVIEW_AGENT), not from tool arguments.
"""
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
ROOTS = [os.path.realpath(p) for p in os.environ.get("RALPH_MCP_ROOTS", "").split(":") if p]
PROTOCOL = "2024-11-05"
SHELLISH = re.compile(r"[;&|<>`]|\$\(")


def needs_shell(cmd):
    """True when a verify command only works in a shell. The driver runs verify commands with shlex.split and no
    shell, so an operator inside quotes is plain text (python3 -c "import sys; sys.exit(0)" is fine) while an unquoted
    ; & | < > ( ), a backtick or $( would be passed to the program as an argument and never do what was meant."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:      # unbalanced quotes
        return True
    return any(t and (set(t) <= set("();<>|&") or t.startswith(("$(", "`"))) for t in tokens)


def project_of(a):
    p = os.path.realpath(os.path.expanduser(a["project_dir"]))
    if not ROOTS:
        raise ValueError("RALPH_MCP_ROOTS is not set; refusing to run anywhere")
    if not any(p == r or p.startswith(r + os.sep) for r in ROOTS):
        raise ValueError(f"project_dir {p} is outside the allowed roots")
    if not os.path.isdir(p):
        raise ValueError(f"project_dir {p} does not exist")
    return p


def rj(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def state_dir(project):
    """Where aistack keeps everything for this project, outside the repository."""
    d = os.environ.get("AISTACK_STATE_DIR")
    if d:
        return os.path.realpath(os.path.expanduser(d))
    home = os.environ.get("AISTACK_HOME") or os.path.expanduser("~/.aistack")
    return os.path.join(home, f"{os.path.basename(project)}-{hashlib.sha1(project.encode()).hexdigest()[:10]}")


def plan_dir(project):
    return os.path.join(state_dir(project), "plan")


def runs_dir(project):
    return os.path.join(state_dir(project), "runs")


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


# ---- plan validation ------------------------------------------------------------
def load_plan(project):
    prd_p = os.path.join(plan_dir(project), "prd.json")
    ver_p = os.path.join(plan_dir(project), "verify.json")
    raw = ""
    for p in (prd_p, ver_p):
        try:
            raw += open(p).read()
        except OSError:
            pass
    return rj(prd_p), rj(ver_p), hashlib.sha256(raw.encode()).hexdigest()[:12]


def validate(prd, verify):
    problems = []
    if not isinstance(prd, dict):
        return ["Missing or invalid prd.json in the plan dir (must be a JSON object)"]
    if not prd.get("name"):
        problems.append("prd.json: 'name' is required")
    if "title" in prd and not (isinstance(prd["title"], str) and prd["title"].strip() and len(prd["title"]) <= 100):
        problems.append("prd.json: 'title' (the pull request title: imperative, no 'feat:' prefix) must be a non-empty string of at most 100 characters")
    if prd.get("type") not in (None, "feat", "fix"):
        problems.append("prd.json: 'type' must be 'feat' or 'fix' when present")
    stories = prd.get("userStories")
    if not isinstance(stories, list) or not stories:
        return problems + ["prd.json: 'userStories' must be a non-empty list"]
    ids = [s.get("id") for s in stories if isinstance(s, dict)]
    for s in stories:
        if not isinstance(s, dict):
            problems.append("prd.json: every userStories entry must be an object")
            continue
        tid = s.get("id")
        if not isinstance(tid, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", tid or ""):
            problems.append(f"story id {tid!r}: use letters, digits, '-' or '_' only")
        if ids.count(tid) > 1:
            problems.append(f"{tid}: duplicate id")
        for k in ("title", "description"):
            if not str(s.get(k, "")).strip():
                problems.append(f"{tid}: '{k}' is required")
        ac = s.get("acceptanceCriteria")
        if not isinstance(ac, list) or not ac or not all(isinstance(x, str) and x.strip() for x in ac):
            problems.append(f"{tid}: 'acceptanceCriteria' must be a non-empty list of strings")
        if not isinstance(s.get("priority"), (int, float)):
            problems.append(f"{tid}: 'priority' must be a number (1 = first)")
        if s.get("passes") is not False:
            problems.append(f"{tid}: 'passes' must be false")
        for d in s.get("dependsOn", []) or []:
            if d not in ids:
                problems.append(f"{tid}: dependsOn {d!r} is not a task id")
    # cycles
    deps = {s["id"]: list(s.get("dependsOn", []) or []) for s in stories if isinstance(s, dict) and "id" in s}
    state = {}

    def visit(n, stack):
        if state.get(n) == 2 or n not in deps:
            return
        if state.get(n) == 1:
            problems.append("dependsOn cycle: " + " -> ".join(stack + [n]))
            return
        state[n] = 1
        for d in deps[n]:
            visit(d, stack + [n])
        state[n] = 2
    for n in list(deps):
        visit(n, [])
    if not isinstance(verify, dict):
        problems.append("Missing or invalid verify.json in the plan dir (object mapping task id -> list of commands)")
        return problems
    for tid in deps:
        cmds = verify.get(tid)
        if isinstance(cmds, str):
            cmds = [cmds]
        if not cmds or not all(isinstance(c, str) and c.strip() for c in cmds):
            problems.append(f"verify.json: task {tid} needs at least one verify command (an exit-0-on-success shell-free command)")
            continue
        for c in cmds:
            if needs_shell(c):
                problems.append(f"verify.json: {tid}: no shell syntax (; & | < > ` $()) in '{c}'. Verify commands run without a shell. "
                                "Use one plain command (operators inside quotes are fine), or have a task create a check script and run that. "
                                "Never point a verify command at a file that no task creates.")
    for tid in verify:
        if tid not in deps:
            problems.append(f"verify.json: {tid} is not a task id")
    return problems


def present_plan(prd, verify, notes=(), lines=()):
    """The plan as text for the user. The chat agent prints this as it is: when a small model summarized the plan
    itself it left out the acceptance criteria and verify commands and added options of its own."""
    out = [f"PLAN: {prd.get('title') or prd.get('name')}", str(prd.get("description") or "").strip(), ""]
    for s in sorted(prd.get("userStories", []), key=lambda s: s.get("priority", 0)):
        out.append(f"{s['id']}  {s.get('title', '')}" + (f"   (after {', '.join(s['dependsOn'])})" if s.get("dependsOn") else ""))
        out.append(f"    does:   {str(s.get('description', '')).strip()}")
        out += [f"    done when: {c}" for c in s.get("acceptanceCriteria", [])]
        out += [f"    verify: {c}" for c in verify.get(s["id"], [])]
    if notes:
        out += ["", "NOTES FROM CLAUDE:"] + [f"  - {n}" for n in notes]
    out += [""] + [x for x in lines if x]
    out.append("Next: say what to change, or say 'start' to build this plan.")
    return "\n".join(out)


def plan_meta(project, write=None):
    """Claude's notes and the status lines (Lumo, skipped files, billed calls) of the saved plan. They are kept next to
    the plan so they are shown again after every change, and also when the plan first came back invalid."""
    path = os.path.join(plan_dir(project), "plan-meta.json")
    if write is not None:
        with open(path, "w") as f:
            json.dump(write, f, indent=1)
        return write
    return rj(path, {}) or {}


def save_plan_text(project, text):
    path = os.path.join(plan_dir(project), "PLAN.txt")
    with open(path, "w") as f:
        f.write(text + "\n")
    return path


def tool_validate(a):
    project = project_of(a)
    prd, verify, h = load_plan(project)
    problems = validate(prd, verify)
    if problems:
        return {"ok": False, "problems": problems, "plan_dir": plan_dir(project)}
    tasks = [{"id": s["id"], "title": s["title"], "priority": s["priority"], "dependsOn": s.get("dependsOn", []),
              "verify": verify[s["id"]]} for s in prd["userStories"]]
    meta = plan_meta(project)
    text = present_plan(prd, verify, meta.get("notes") or (), meta.get("lines") or ())
    save_plan_text(project, text)
    return {"ok": True, "plan_hash": h, "name": prd["name"], "tasks": tasks, "plan_dir": plan_dir(project),
            "present": text,
            "next": "Show this plan to the user. Only after they confirm it, call ralph_run with this plan_hash."}


# ---- runs -----------------------------------------------------------------------
def latest_run(project):
    d = runs_dir(project)
    if not os.path.isdir(d):
        return None
    names = sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))
    return names[-1] if names else None


def run_state(project, rid):
    st = rj(os.path.join(runs_dir(project), rid, "state.json"), {})
    if st.get("state") in ("running", "waiting_user", "starting") and not alive(st.get("pid")):
        age = time.time() - os.path.getmtime(os.path.join(runs_dir(project), rid, "state.json")) \
            if os.path.exists(os.path.join(runs_dir(project), rid, "state.json")) else 0
        if st.get("pid") or age > 20:
            st["state"] = "lost"
    return st


# gpr's AI interface: --auto never prompts, --title/--description become the PR title and body, the last stdout line is
# JSON ({"ok","branch","worktree","pr_url","pr_number"}); AISTACK_BRANCH / _PR_TYPE / _PR_TITLE / _PR_BODY are set below
DEFAULT_WORKTREE_CMD = ("source ~/.zshrc_functions_git 2>/dev/null; source ~/.zshrc_functions_ai 2>/dev/null; "
                        "gpr_func --auto \"$AISTACK_PR_TYPE\" \"$AISTACK_BRANCH\" --title \"$AISTACK_PR_TITLE\" "
                        "--description \"$AISTACK_PR_BODY\"")


def pr_title_and_body(prd, verify):
    """The draft PR's title and description, from the plan: prd.json 'title' (falls back to 'name'), its description,
    the tasks with acceptance criteria and verify commands, and which tiers do the work."""
    ptype = prd.get("type") or "feat"
    text = str(prd.get("title") or prd.get("name") or "aistack plan").strip()
    text = re.sub(r"^(feat|fix)(\([^)]*\))?:\s*", "", text, flags=re.IGNORECASE)
    title = f"{ptype}: {text}"
    if len(title) > 72:
        title = title[:71].rstrip() + "\u2026"
    lines = ["## Summary", str(prd.get("description") or prd.get("name") or "").strip(), "", "## Plan"]
    for st in prd.get("userStories", []):
        crit = "; ".join(st.get("acceptanceCriteria", []))
        v = verify.get(st["id"], []) if isinstance(verify, dict) else []
        v = [v] if isinstance(v, str) else v
        lines.append(f"- **{st['id']}** {st.get('title', '')}" + (f": {crit}" if crit else "")
                     + (" (verify: " + ", ".join(f"`{c}`" for c in v) + ")" if v else ""))
    lines += ["", "---", "Opened by aistack when the plan was confirmed. "
              + (os.environ.get("AISTACK_TIERS", "") + ". " if os.environ.get("AISTACK_TIERS") else "")
              + "Changes stay uncommitted in this worktree until committed with gpc/gpa."]
    return ptype, title, "\n".join(lines)


def ensure_workdir(project, prd, verify=None):
    """Where the agents work. In a main checkout (AISTACK_WORKTREE_MODE=create) the first confirmed plan creates a gpr
    worktree + draft PR, later runs reuse it while it exists. Elsewhere the project itself is the work dir."""
    meta_p = os.path.join(state_dir(project), "project.json")
    meta = rj(meta_p, {})
    if meta.get("work_dir") and os.path.isdir(meta["work_dir"]):
        return meta["work_dir"], False, None
    if os.environ.get("AISTACK_WORKTREE_MODE") != "create":
        return project, False, None
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(prd.get("name", "plan")).lower())).strip("-")[:28] or "plan"
    branch = f"aistack-{slug}-{time.strftime('%H%M')}"
    ptype, title, body = pr_title_and_body(prd, verify or {})
    env = dict(os.environ, AISTACK_BRANCH=branch, AISTACK_PR_TYPE=ptype, AISTACK_PR_TITLE=title, AISTACK_PR_BODY=body)
    cmd = os.environ.get("AISTACK_WORKTREE_CMD")
    argv = ["/bin/sh", "-c", cmd] if cmd else ["zsh", "-c", DEFAULT_WORKTREE_CMD]
    try:
        r = subprocess.run(argv, cwd=project, env=env, capture_output=True, text=True, timeout=170, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, False, f"creating the worktree failed: {e}"
    result = {}
    for line in reversed((r.stdout or "").strip().splitlines()):
        try:
            result = json.loads(line)
            break
        except ValueError:
            continue
    wd = result.get("worktree") or os.path.join(project, ".worktrees", branch)
    if not os.path.isdir(wd):
        tail = (r.stdout + r.stderr)[-600:]
        return None, False, f"creating the worktree {wd} failed (exit {r.returncode}): {tail}"
    meta.update(work_dir=wd, branch=branch, source_dir=project, created=time.strftime("%Y-%m-%dT%H:%M:%S"),
                pr_url=result.get("pr_url"), pr_number=result.get("pr_number"), pr_title=title)
    os.makedirs(state_dir(project), exist_ok=True)
    json.dump(meta, open(meta_p, "w"), indent=2)
    return wd, True, None


def plan_review_path(project):
    return os.path.join(state_dir(project), "plan-review.json")


# ---- aidev: Claude Code writes the plan (one billed call) instead of reviewing one -------------------------------
# The chat agent (the local model) does the research for free and passes it in: a brief, the files that matter
# (inlined here, so the local model does not have to copy code through its own output), and Lumo's draft if any.
# Claude returns the finished prd.json + verify.json; nothing has to apply review findings afterwards.
# Both caps bound what one billed Claude call can be handed. The brief is the local model's own words. The draft is
# Lumo's and carries its online research: 60,000 characters is about the most one Lumo reply holds (measured by
# Josh), so a draft reaches Claude whole (it was cut at 12,000 on the first real run). That is up to about 15,000
# tokens of Claude input per plan. Anything longer is cut at a paragraph, visibly.
PLAN_BRIEF_MAX, PLAN_DRAFT_MAX = 16_000, 60_000
# A long draft is not passed on as it is: Lumo gets it back in a fresh request and shortens it (free), so Claude is
# not routinely billed for tens of thousands of characters. Only when that second request fails, or does not come back
# shorter, does the long draft go through (up to PLAN_DRAFT_MAX).
DRAFT_CONDENSE_AT = int(os.environ.get("AISTACK_LUMO_CONDENSE_AT", "12000"))
CONDENSE_PROMPT = """Below is a draft build plan. Rewrite it in at most 1200 words for a senior engineer who will turn it into tasks.
Keep: every concrete task, every file path, command, tool name and version number, each fact you found online together with
its source, and the open questions. Drop: introductions, explanations of well-known things, repetition, praise and summaries
of the project. Use short numbered items. Do not add anything that is not in the draft.

DRAFT:
"""
PLAN_PROMPT = """You write the build plan for a coding run. Cheaper agents build it: a free coding model implements one task per
session, a harness counts a task as done only when that task's verify commands exit 0, and you review the whole result once at the end.
A plan that is vague or has weak verify commands costs failed attempts, so be exact.

Below: the user's request, a research brief written by a small local model (it can be wrong or incomplete), the project files it
picked, and possibly a draft plan from another assistant (treat it as a draft, keep only what fits the code).
Plan in ONE turn from what is below. The project files are excerpts with line numbers, chosen for this request. You may make at
most 2 lookups (Read, Grep or Glob), each to check one specific claim the plan depends on. Do not explore, and do not modify anything.
%s

Reply with ONE JSON object and nothing else (no prose, no code fence):
{"prd": {"name": "short-slug", "title": "...", "description": "...", "userStories": [
   {"id": "T1", "title": "...", "description": "...", "acceptanceCriteria": ["..."], "priority": 1, "passes": false, "dependsOn": []}]},
 "verify": {"T1": ["command"]},
 "notes": ["assumption or open question for the user"]}

Rules:
- prd.title is the pull request title: imperative, at most 72 characters, no "feat:" prefix. prd.description is the pull request
  summary: two to four sentences on what changes and why.
- Each task fits one agent session. Its description names the files to create or change and the exact behavior, with enough detail
  that a weaker model does not have to guess (function names, signatures, where it is called from, edge cases).
- acceptanceCriteria are concrete and testable. priority 1 runs first; use dependsOn when a task needs another finished.
  passes is always false. Ids use letters, digits, - or _.
- verify maps EVERY task id to at least one command that exits 0 only when that task is really done and does not pass on
  unrelated or empty state (tests, a linter, a build, a check script). Commands run without a shell: no ; & | < > backtick or $().
  When a check needs several steps, make the task create a script file and run that. Name test files in the task description.
- notes: only what the user must know or decide. Use [] when there is nothing.
- A broad request (evaluate, review, audit, "what can I improve") is still a request for a plan: choose the improvements
  that matter most, at most 6, each one a concrete task that can be built and verified like any other. Put further findings,
  and anything that is advice and not a change, in notes (one line each, most important first). Do not plan a task on a
  claim from the brief or the draft that you have not checked in the code.

USER REQUEST:
%s

RESEARCH BRIEF:
%s
%s%s"""


# Every Claude turn re-reads the whole prompt, and three real runs spent 4-5 turns on 7-10 lookups. So Claude is told
# to plan in one turn, and given a cheaper way out than exploring: say what is missing. The local model then looks it
# up and Lumo revises its draft (both free), and Claude gets exactly one more call.
NEED_NOTE = """If that is not enough to write exact tasks, do not explore further and do not guess. Reply with this INSTEAD of a plan, and
you will be called once more with the answers:
{"need": {"from_local_model": ["a specific question, or a file and what to look for in it"], "for_lumo": "what its draft should cover or correct, or an empty string"}}
Ask only for what would change the plan, at most 6 questions."""
FINAL_NOTE = """This is the final attempt: you asked for more before, and the answers are in the brief and the files below. Write the plan
now. Put anything still unknown in notes. Do not ask again."""
REVISE_PROMPT = """A planner reviewed your draft build plan and asks for this before it can use it:

%s

Rewrite the draft accordingly, in at most 1200 words, as short numbered items. Keep what was right, keep file paths, commands,
versions and sources, and do not add praise or explanations of well-known things.

YOUR DRAFT:
%s"""
# Files go to Claude as excerpts. A whole file is accepted only when it is short; a longer one is refused once, before
# anything is billed, so the local model picks the lines that matter (repo_read and repo_grep show line numbers).
FILE_WHOLE_MAX_LINES = int(os.environ.get("AISTACK_PLAN_WHOLE_FILE_LINES", "120"))
RANGE_MAX_LINES = int(os.environ.get("AISTACK_PLAN_RANGE_LINES", "200"))
PLAN_FILES_TOTAL_MAX = int(os.environ.get("AISTACK_PLAN_FILES_CHARS", "24000"))
_RANGES_ASKED = set()


def file_line_count(project, rel):
    """Lines in a project file that may be sent, or None (missing, denied, binary)."""
    text, why = lumo_readable(project, rel)
    if text is None and why and why.startswith("larger than"):
        try:
            text = open(os.path.realpath(os.path.join(project, rel)), encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            return None
    return None if text is None else len(text.splitlines())


def need_path(project):
    return os.path.join(plan_dir(project), "need.json")


def extract_need(text):
    """Claude's 'I need more' reply: the first JSON object with a 'need' object, or None."""
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("need"), dict):
            return obj["need"]
    return None


def plan_file(project, spec):
    """(rel, text, None) or (rel, None, reason) for one `files` entry: a relative path, optionally with a line range
    ('lib/a.py:40-120'). Uses the same deny list as Lumo; a range may come from a file too big to send whole."""
    m = re.match(r"^(.*?):(\d+)-(\d+)$", spec)
    rel = m.group(1) if m else spec
    text, why = lumo_readable(project, rel)
    if text is None and m and why and why.startswith("larger than"):
        # lumo_readable checks path and deny list before size, so only the size limit stands in the way here
        try:
            text = open(os.path.realpath(os.path.join(project, rel)), encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            return rel, None, "unreadable or binary"
    if text is None:
        return rel, None, why
    if m:
        lo, hi = max(int(m.group(2)), 1), int(m.group(3))
        lines = text.splitlines()[lo - 1:hi]
        if not lines:
            return rel, None, "line range is empty"
        text = "\n".join(f"{lo + i}: {ln}" for i, ln in enumerate(lines)) + "\n"
        if len(text) > LUMO_FILE_MAX:
            return rel, None, f"range larger than {LUMO_FILE_MAX} bytes"
    return rel, text, None


def extract_plan(text):
    """The first JSON object in Claude's reply that has a 'prd' object, or None."""
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("prd"), dict):
            return obj
    return None


def tool_plan(a):
    global RESEARCH_CALLS
    project = project_of(a)
    request = (a.get("request") or "").strip()
    if not request:
        return {"ok": False, "problem": "request is empty"}
    prev = rj(plan_review_path(project), {})
    if prev.get("source") == "claude-plan" and not a.get("replan"):
        _, _, h = load_plan(project)
        return {"ok": True, "already_planned": True, "plan_hash": h, "planned_request": prev.get("request"), "billed_calls": 0,
                "next": "Claude already wrote a plan that has not been run yet (planned_request). If it is for the same work, call "
                        "ralph_validate_plan and show it to the user. Pass replan=true only when the user wants a new plan (billed)."}
    # Long files must come as line ranges. Refused once, before Lumo or Claude is asked, with the line counts.
    specs = [str(f) for f in (a.get("files") or [])][:LUMO_FILES_MAX]
    too_long = {}
    for spec in specs:
        if not re.search(r":\d+-\d+$", spec):
            n = file_line_count(project, spec)
            if n and n > FILE_WHOLE_MAX_LINES:
                too_long[spec] = n
    if too_long and project not in _RANGES_ASKED:
        _RANGES_ASKED.add(project)
        return {"ok": False, "billed_calls": 0, "files_need_ranges": too_long,
                "problem": f"Nothing was sent yet. These files are longer than {FILE_WHOLE_MAX_LINES} lines (line counts given) and must be "
                           "sent as the lines that matter, not whole.",
                "next": f"Call ralph_plan again with the same request and brief, giving each of these files as path:START-END "
                        f"(at most {RANGE_MAX_LINES} lines per range; the same file may appear twice with different ranges). Use the line "
                        "numbers you saw in repo_read and repo_grep. Do not tell the user about this step."}
    brief, draft = (a.get("brief") or "").strip(), (a.get("draft") or "").strip()
    brief_cut = len(brief) > PLAN_BRIEF_MAX
    brief = brief[:PLAN_BRIEF_MAX]
    # A second call after Claude asked for more: it is the final attempt, and Lumo's revised draft is reused.
    prior_need = rj(need_path(project), {}) or {}
    final_attempt = bool(prior_need)
    if prior_need.get("draft"):
        draft = prior_need["draft"]
    # Lumo (free, can look things up online) is asked here, not by the chat agent: the small local model skipped that
    # step when it was its job. Only when the launcher found a Lumo (AISTACK_TIER0=lumo) and no draft was passed in.
    lumo_state = ("draft revised by Lumo after Claude asked for changes" if prior_need.get("draft")
                  else "draft passed in" if draft else "not available")
    if not draft and os.environ.get("AISTACK_TIER0") == "lumo":
        lr = tool_lumo_consult({"project_dir": project, "request": request + ("\n\nWhat a local model found in the code:\n" + brief[:6000] if brief else ""),
                                "files": [re.sub(r":\d+-\d+$", "", str(f)) for f in (a.get("files") or [])],
})
        if lr.get("ok"):
            draft, lumo_state = str(lr.get("plan") or "").strip(), "consulted (" + str(lr.get("lumo", "")) + ")"
            if lr.get("lumo_asked_for"):
                lumo_state += f", it asked for {len(lr['lumo_asked_for'])} more thing(s) from the project and got them"
            if len(draft) > DRAFT_CONDENSE_AT:
                cr = tool_lumo_consult({"project_dir": project, "request": "condense", "raw_prompt": CONDENSE_PROMPT + draft[:PLAN_DRAFT_MAX],
        })
                short = str(cr.get("plan") or "").strip() if cr.get("ok") else ""
                if 400 <= len(short) < len(draft):
                    lumo_state += f", its draft shortened by Lumo from {len(draft)} to {len(short)} characters"
                    draft = short
                else:
                    lumo_state += f", its {len(draft)}-character draft could not be shortened and went to Claude as it is"
        else:
            lumo_state = "failed: " + str(lr.get("problem", ""))[:160]
    truncated = ["brief"] if brief_cut else []
    if len(draft) > PLAN_DRAFT_MAX:
        cut = draft.rfind("\n\n", 0, PLAN_DRAFT_MAX)
        draft = draft[:cut if cut > PLAN_DRAFT_MAX // 2 else PLAN_DRAFT_MAX] + "\n\n[the draft was longer and is cut here]"
        truncated.append("draft")
    sent, skipped, blocks, total, trimmed = [], {}, [], 0, []
    for spec in specs:
        m = re.search(r":(\d+)-(\d+)$", spec)
        if m and int(m.group(2)) - int(m.group(1)) + 1 > RANGE_MAX_LINES:
            lo = int(m.group(1))
            spec = f"{spec[:m.start()]}:{lo}-{lo + RANGE_MAX_LINES - 1}"; trimmed.append(spec)
        elif not m and spec in too_long:        # still whole after being asked for a range: its head only
            spec = f"{spec}:1-{FILE_WHOLE_MAX_LINES}"; trimmed.append(spec)
        _, text, why = plan_file(project, spec)
        if text is None:
            skipped[spec] = why
        elif total + len(text) > PLAN_FILES_TOTAL_MAX:
            skipped[spec] = "total size limit reached"
        else:
            total += len(text); sent.append(spec); blocks.append(f"\n--- FILE: {spec} ---\n{text}")
    prompt = PLAN_PROMPT % (FINAL_NOTE if final_attempt else NEED_NOTE, request, brief or "(none)",
                            "\nPROJECT FILES:" + "".join(blocks) if blocks else "",
                            "\nDRAFT PLAN FROM ANOTHER ASSISTANT:\n" + draft if draft else "")
    cmd = os.environ.get("AISTACK_PLAN_CMD")
    argv = ["/bin/sh", "-c", cmd] if cmd else [os.path.join(HERE, "claude-plan.sh"), "-p", prompt]
    env = dict(os.environ, AISTACK_WORKDIR=project, AISTACK_PLAN_PROMPT=prompt)
    try:
        r = subprocess.run(argv, cwd=project, env=env, capture_output=True, text=True,
                           timeout=int(os.environ.get("AISTACK_PLAN_TIMEOUT_S", "280")), stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "problem": f"the planning call (Claude Code) did not finish: {type(e).__name__}: {e}"}
    text = (r.stdout or "").strip()
    plan = extract_plan(text) if r.returncode == 0 else None
    os.makedirs(plan_dir(project), exist_ok=True)
    need = extract_need(text) if (r.returncode == 0 and not plan and not final_attempt) else None
    questions = [str(q) for q in (need or {}).get("from_local_model") or [] if str(q).strip()][:6]
    feedback = str((need or {}).get("for_lumo") or "").strip()
    if need and (questions or feedback):
        revised = ""
        if feedback and draft and os.environ.get("AISTACK_TIER0") == "lumo":
            rr = tool_lumo_consult({"project_dir": project, "request": "revise", "raw_prompt": REVISE_PROMPT % (feedback, draft)})
            if rr.get("ok") and len(str(rr.get("plan") or "").strip()) >= 400:
                revised = str(rr["plan"]).strip()[:PLAN_DRAFT_MAX]
        with open(need_path(project), "w") as f:
            json.dump({"questions": questions, "for_lumo": feedback, "draft": revised or draft, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, f, indent=1)
        RESEARCH_CALLS = 0      # the questions get their own research budget
        return {"ok": False, "needs_more": True, "billed_calls": 1, "questions": questions,
                "lumo": ("Lumo revised its draft as Claude asked" if revised else "Claude's note for Lumo could not be applied" if feedback else "no change asked of Lumo"),
                "problem": "Claude needs more before it can write the plan.",
                "next": "Tell the user in one line that Claude asked for more detail and that the next call is billed too. Then answer "
                        "each question with repo_tree / repo_read / repo_grep (you have a fresh budget), and call ralph_plan again with "
                        "the same request, a brief that now includes the answers, and files as line ranges that show them. That call is "
                        "the last: Claude will plan with what it gets. Ask the user only if a question is about what they want."}
    if not plan:
        raw = os.path.join(plan_dir(project), "claude-plan.raw.txt")
        with open(raw, "w") as f:
            f.write(text + "\n" + (r.stderr or ""))
        return {"ok": False, "problem": f"Claude returned no plan (exit {r.returncode}); its output is in {raw}",
                "tail": (text or r.stderr or "")[-600:], "billed_calls": 1,
                "next": "Tell the user. Do not call ralph_plan again unless they ask (each call is billed)."}
    prd = plan["prd"]
    verify = plan.get("verify") if isinstance(plan.get("verify"), dict) else {}
    for s in prd.get("userStories") or []:
        if isinstance(s, dict):
            s["passes"] = False
    verify = {k: [v] if isinstance(v, str) else v for k, v in verify.items()}
    for name, obj in (("prd.json", prd), ("verify.json", verify)):
        with open(os.path.join(plan_dir(project), name), "w") as f:
            json.dump(obj, f, indent=1)
    _, _, h = load_plan(project)
    # ralph_run wants a Claude verdict on the plan before building; a plan Claude wrote itself has one by construction
    json.dump({"plan_hash": h, "name": prd.get("name"), "verdict": "PLANNED", "source": "claude-plan", "request": request[:500],
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, open(plan_review_path(project), "w"))
    problems = validate(prd, verify)
    notes = [str(n) for n in plan.get("notes") or []][:12] if isinstance(plan.get("notes"), list) else []
    lines = [x for x in (
        f"Lumo: {lumo_state}.",
        "Not sent to Claude: " + ", ".join(f"{k} ({v})" for k, v in skipped.items()) + "." if skipped else "",
        "Cut to the size limit: " + ", ".join(truncated) + "." if truncated else "",
        "Sent only in part (a range was needed or too long): " + ", ".join(trimmed) + "." if trimmed else "",
        "Claude asked for more detail once before planning (2 billed calls for this plan)." if final_attempt else "",
        "" if final_attempt else "Claude Code: 1 billed call for this plan; it reviews the result once more at the end.") if x]
    try:
        os.remove(need_path(project))
    except OSError:
        pass
    plan_meta(project, {"notes": notes, "lines": lines})
    # Only the finished text goes back, with nothing next to it to summarize from: handed the tasks and notes as
    # data as well, the local model wrote its own version of the plan.
    out = {"ok": not problems, "plan_hash": h, "billed_calls": 1, "lumo": lumo_state}
    try:
        out["present"] = present_plan(prd, verify, notes, lines)
        out["plan_file"] = save_plan_text(project, out["present"])
    except Exception:       # a plan too malformed to print: the problems below say what is wrong
        out["present"] = ""
    if problems:
        out.update(problems=problems, next="Claude's plan is saved but not valid yet. Fix each problem with ralph_update_task (for a "
                   "verify command: one plain command without unquoted ; & | < > and never a file that no task creates). When "
                   "ralph_update_task returns ok=true, reply with its 'present' in a code block as usual. Do NOT call ralph_plan "
                   "again: it is billed and the plan already exists.")
        return out
    out["next"] = ("Your whole reply is: one code block (three backticks) containing the text of 'present' copied character for "
                   "character, then the single line: Change something, or start? Nothing else. No heading, no summary, no "
                   "markdown inside the block. Later: a change is ralph_update_task; 'start' is ralph_run with this plan_hash.")
    RESEARCH_CALLS = 0      # the plan exists: a later question from the user gets a fresh, equally small budget
    return out


# ---- aidev: the local model's only way to look at the project ----------------------------------------------------
# With pi's own read/ls/grep the small model made 90 calls on one request (about 70 of them ls) although the prompt
# said 12. These three tools count: past the budget they refuse and say to call ralph_plan. repo_tree answers in one
# call what took dozens of ls. They read tracked files only where git can say so, and refuse what Lumo may not see.
RESEARCH_BUDGET = int(os.environ.get("AISTACK_RESEARCH_CALLS", "16"))
RESEARCH_CALLS = 0
READ_MAX_LINES, READ_MAX_CHARS, GREP_MAX, TREE_MAX = 400, 24_000, 60, 400


def research(fn):
    def wrapped(a):
        global RESEARCH_CALLS
        project = project_of(a)
        if RESEARCH_CALLS >= RESEARCH_BUDGET:
            return {"ok": False, "calls_left": 0, "problem": f"The research budget ({RESEARCH_BUDGET} calls) is used up. Do not look "
                    "further: call ralph_plan now with the request, a brief of what you found, and the files that matter. "
                    "Claude Code can look up what is missing."}
        RESEARCH_CALLS += 1
        out = fn(project, a)
        out["calls_left"] = RESEARCH_BUDGET - RESEARCH_CALLS
        if out["calls_left"] <= 3:
            out["note"] = f"{out['calls_left']} research calls left, then call ralph_plan."
        return out
    return wrapped


def project_files(project):
    """Relative paths of the project's files: what git tracks (plus untracked, not ignored), else a plain walk."""
    r = subprocess.run(["git", "-C", project, "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        return [f for f in r.stdout.splitlines() if f]
    out = []
    for base, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in LUMO_DENY_DIRS]
        out += [os.path.relpath(os.path.join(base, f), project) for f in files]
    return out


@research
def tool_repo_tree(project, a):
    sub = str(a.get("path") or "").strip("/")
    depth = max(1, min(int(a.get("depth") or 2), 4))
    files = [f for f in project_files(project) if not sub or f == sub or f.startswith(sub + "/")]
    if not files:
        return {"ok": False, "problem": f"nothing under {sub!r}. That path is your guess, not a problem in the project; call repo_tree without a path to see what exists."}
    dirs, shown = {}, []
    for f in sorted(files):
        parts = (f[len(sub):].lstrip("/") if sub else f).split("/")
        if len(parts) <= depth:
            shown.append("/".join(parts))
        else:
            key = "/".join(parts[:depth]) + "/"
            dirs[key] = dirs.get(key, 0) + 1
    lines = shown + [f"{d}  ({n} files below)" for d, n in sorted(dirs.items())]
    return {"ok": True, "path": sub or ".", "files_total": len(files),
            "entries": sorted(lines)[:TREE_MAX], "cut": len(lines) > TREE_MAX}


@research
def tool_repo_read(project, a):
    rel = str(a.get("path") or "")
    text, why = lumo_readable(project, rel)
    if text is None and why and why.startswith("larger than"):
        try:
            text = open(os.path.realpath(os.path.join(project, rel)), encoding="utf-8").read()   # read in pieces below
        except (UnicodeDecodeError, OSError):
            why = "unreadable or binary"
    if text is None:
        return {"ok": False, "problem": f"{rel}: {why}" + (". That path is your guess, not a problem in the project." if why == "not a file" else "")}
    lines = text.splitlines()
    lo = max(int(a.get("start") or 1), 1)
    hi = min(int(a.get("end") or lo + READ_MAX_LINES - 1), lo + READ_MAX_LINES - 1, len(lines))
    body = "\n".join(f"{lo + i}: {ln}" for i, ln in enumerate(lines[lo - 1:hi]))[:READ_MAX_CHARS]
    return {"ok": True, "path": rel, "lines": f"{lo}-{hi} of {len(lines)}", "text": body}


@research
def tool_repo_grep(project, a):
    pattern = str(a.get("pattern") or "")
    if not pattern:
        return {"ok": False, "problem": "pattern is required"}
    argv = ["git", "-C", project, "grep", "-n", "-I", "-E", "-e", pattern]
    if a.get("path"):
        argv += ["--", str(a["path"])]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    if r.returncode not in (0, 1):
        r = subprocess.run(["grep", "-rnIE", "--exclude-dir=.git", "-e", pattern, str(a.get("path") or ".")], cwd=project, capture_output=True, text=True, timeout=30)
    hits = []
    for ln in r.stdout.splitlines():
        rel = ln.split(":", 1)[0]
        if lumo_readable(project, rel)[1] == "denied by policy":
            continue
        hits.append(ln[:220])
    return {"ok": True, "matches": hits[:GREP_MAX], "matches_total": len(hits), "cut": len(hits) > GREP_MAX}


def tool_update_task(a):
    """Change, add or remove ONE task in the saved plan, with its verify commands. In aidev the chat agent has no
    write or edit tool, so this is how it applies a small change the user asked for or fixes a validation problem;
    it can only ever touch prd.json and verify.json in the plan dir."""
    project = project_of(a)
    prd, verify, _ = load_plan(project)
    if not isinstance(prd, dict) or not isinstance(prd.get("userStories"), list):
        return {"ok": False, "problem": "there is no plan yet: call ralph_plan first"}
    verify = verify if isinstance(verify, dict) else {}
    tid = str(a.get("task_id") or "").strip()
    if not tid:
        return {"ok": False, "problem": "task_id is required"}
    stories = prd["userStories"]
    cur = next((s for s in stories if isinstance(s, dict) and s.get("id") == tid), None)
    if a.get("remove"):
        if not cur:
            return {"ok": False, "problem": f"{tid} is not a task id"}
        stories.remove(cur)
        verify.pop(tid, None)
        for s in stories:
            if isinstance(s, dict) and tid in (s.get("dependsOn") or []):
                s["dependsOn"] = [d for d in s["dependsOn"] if d != tid]
    else:
        if not cur:
            cur = {"id": tid, "passes": False, "dependsOn": [], "priority": max([s.get("priority", 0) for s in stories if isinstance(s, dict)] + [0]) + 1}
            stories.append(cur)
        for k in ("title", "description", "acceptanceCriteria", "priority", "dependsOn"):
            if a.get(k) is not None:
                cur[k] = a[k]
        cur["passes"] = False
        if a.get("verify") is not None:
            verify[tid] = [a["verify"]] if isinstance(a["verify"], str) else a["verify"]
    for name, obj in (("prd.json", prd), ("verify.json", verify)):
        with open(os.path.join(plan_dir(project), name), "w") as f:
            json.dump(obj, f, indent=1)
    out = tool_validate({"project_dir": project})
    out["changed"] = ("removed " if a.get("remove") else "updated ") + tid
    return out


def tool_run(a):
    project = project_of(a)
    prd, verify, h = load_plan(project)
    problems = validate(prd, verify)
    if problems:
        return {"started": False, "problems": problems}
    if a.get("plan_hash") != h:
        return {"started": False, "problem": "plan_hash does not match the current plan. Call ralph_validate_plan, show the user the result, get their confirmation, then pass the plan_hash it returns."}
    if os.environ.get("AISTACK_PLAN_REVIEW", "on") != "off" and not a.get("skip_plan_review"):
        rev = rj(plan_review_path(project), {})
        if not rev.get("verdict"):
            return {"started": False, "problem": "This plan was not written by Claude Code (or it already ran once). Call ralph_plan "
                    "first; it writes and records the plan. Pass skip_plan_review=true only if the user explicitly said to run a "
                    "plan Claude did not write."}
    rid0 = latest_run(project)
    if rid0 and run_state(project, rid0).get("state") in ("running", "waiting_user", "starting"):
        return {"started": False, "problem": f"run {rid0} is still active; use ralph_status / ralph_respond / ralph_cancel"}
    workdir, created, err = ensure_workdir(project, prd, verify)
    if err:
        return {"started": False, "problem": err}
    rid = time.strftime("%Y%m%d-%H%M%S")
    d = os.path.join(runs_dir(project), rid)
    os.makedirs(d, exist_ok=True)
    env = os.environ
    cfg = {"prd": os.path.join(plan_dir(project), "prd.json"), "verify": os.path.join(plan_dir(project), "verify.json"),
           "work_dir": workdir, "state_dir": state_dir(project),
           "worker_agent": env.get("AISTACK_WORKER_AGENT", "opencode-pickle"),
           "fallback_agent": env.get("AISTACK_FALLBACK_AGENT", "claude-work"),
           "reviewer_agent": env.get("AISTACK_REVIEW_AGENT", "claude-review"),
           "work_template": env.get("AISTACK_WORK_TEMPLATE", os.path.join(HERE, "task-template.hbs")),
           "review_template": env.get("AISTACK_REVIEW_TEMPLATE", os.path.join(HERE, "review-template.hbs")),
           "worker_attempts": int(env.get("AISTACK_WORKER_ATTEMPTS", "2")),
           "fallback_attempts": int(env.get("AISTACK_FALLBACK_ATTEMPTS", "1")),
           "attempt_timeout_s": int(env.get("AISTACK_ATTEMPT_TIMEOUT_S", "1500")),
           "verify_timeout_s": int(env.get("AISTACK_VERIFY_TIMEOUT_S", "300")),
           "review_mode": env.get("AISTACK_REVIEW_MODE", "batch"),
           "ralph_bin": env.get("RALPH_TUI_BIN", os.path.expanduser("~/.bun/bin/ralph-tui"))}
    # agents whose calls cost money (Claude Code); AISTACK_BILLED_AGENTS (comma list) overrides
    named = [cfg["worker_agent"], cfg["fallback_agent"], cfg["reviewer_agent"]]
    cfg["billed_agents"] = ([x for x in env["AISTACK_BILLED_AGENTS"].split(",") if x] if "AISTACK_BILLED_AGENTS" in env
                            else sorted({x for x in named if x.startswith("claude")}))
    json.dump(cfg, open(os.path.join(d, "config.json"), "w"), indent=2)
    driver = env.get("AISTACK_DRIVER", os.path.join(HERE, "ralph_driver.py"))
    log = open(os.path.join(d, "driver.log"), "w")
    p = subprocess.Popen([sys.executable, driver, state_dir(project), rid], cwd=workdir, stdin=subprocess.DEVNULL,
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    json.dump({"state": "starting", "pid": p.pid, "run_id": rid}, open(os.path.join(d, "state.json"), "w"))
    # the review covers one run: a later plan in this project is a new plan and gets its own review
    try:
        os.remove(plan_review_path(project))
    except OSError:
        pass
    return {"started": True, "run_id": rid, "work_dir": workdir, "worktree_created": created,
            "pr_url": rj(os.path.join(state_dir(project), "project.json"), {}).get("pr_url"),
            "worker": cfg["worker_agent"], "fallback": cfg["fallback_agent"],
            "reviewer": cfg["reviewer_agent"], "next": "Call ralph_status with wait_s=40 repeatedly and relay each batch of new events to the user."}


def trim(ev):
    out = {}
    for k, v in ev.items():
        if isinstance(v, str) and len(v) > 1200:
            v = v[:1200] + "..."
        out[k] = v
    return out


def tool_status(a):
    project = project_of(a)
    rid = a.get("run_id") or latest_run(project)
    if not rid:
        return {"error": "no runs in this project yet"}
    since = int(a.get("since", 0))
    deadline = time.time() + min(max(float(a.get("wait_s", 0)), 0), 45)
    first = rj(os.path.join(runs_dir(project), rid, "state.json"), {})
    (first.get("state"), first.get("last_seq"))
    while True:
        st = run_state(project, rid)
        evs = []
        try:
            for line in open(os.path.join(runs_dir(project), rid, "events.jsonl")):
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e["seq"] > since:
                    evs.append(trim(e))
        except OSError:
            pass
        terminal = st.get("state") in ("done", "cancelled", "failed", "lost")
        if evs or terminal or st.get("state") == "waiting_user" or time.time() >= deadline:
            break
        time.sleep(1)
    tasks = {t: {k: v for k, v in d.items() if k in ("title", "status", "attempts", "agent", "review")}
             for t, d in (st.get("tasks") or {}).items()}
    return {"run_id": rid, "state": st.get("state"), "phase": st.get("phase"), "current_task": st.get("current_task"),
            "waiting_for": st.get("waiting_for"), "tasks": tasks, "events": evs,
            "last_seq": max([e["seq"] for e in evs], default=since),
            "hint": "pass since=last_seq on the next call" + ("; the run needs the user: ask them, then call ralph_respond" if st.get("state") == "waiting_user" else "")}


def tool_respond(a):
    project = project_of(a)
    rid = a.get("run_id") or latest_run(project)
    st = run_state(project, rid) if rid else {}
    if st.get("state") != "waiting_user":
        return {"sent": False, "problem": f"run is not waiting for the user (state: {st.get('state')})"}
    allowed = (st.get("waiting_for") or {}).get("options", [])
    act = a.get("action")
    if act not in allowed:
        return {"sent": False, "problem": f"action {act!r} is not valid now; valid: {allowed}"}
    msg = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": act, "text": a.get("text", ""), "task": a.get("task_id")}
    if a.get("tasks"):
        msg["tasks"] = a["tasks"]
    with open(os.path.join(runs_dir(project), rid, "control.jsonl"), "a") as f:
        f.write(json.dumps(msg) + "\n")
    return {"sent": True, "action": act}


def tool_cancel(a):
    project = project_of(a)
    rid = a.get("run_id") or latest_run(project)
    st = run_state(project, rid) if rid else {}
    if st.get("state") in ("done", "cancelled", "failed", "lost") or not st:
        return {"cancelled": False, "problem": f"nothing to cancel (state: {st.get('state')})"}
    try:
        os.kill(st["pid"], signal.SIGTERM)
    except (OSError, KeyError) as e:
        return {"cancelled": False, "problem": str(e)}
    return {"cancelled": True, "run_id": rid}


def tool_runs(a):
    project = project_of(a)
    d = runs_dir(project)
    out = []
    for n in (sorted(os.listdir(d)) if os.path.isdir(d) else []):
        st = run_state(project, n)
        out.append({"run_id": n, "state": st.get("state"), "phase": st.get("phase")})
    return {"runs": out}


# ---- tier 0: Lumo (Proton's cloud assistant) as a tool-less drafting consultant -------------------------
# Lumo cannot call tools, and the planner proxy (nix-modules/macos/lumo.nix) serves the Mini's own checkout,
# not this project, so everything Lumo needs is sent inline. Only files the caller lists are sent, and never
# ones matching the deny list below (secrets, keys, env files, state).
LUMO_DENY_DIRS = {".git", "node_modules", ".terraform", "secrets", ".ssh", ".gnupg", ".aistack", ".ralph-tui"}
LUMO_DENY_GLOBS = [".env*", "*.tfvars", "*.tfstate*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*",
                   "*kubeconfig*", "*.age", "*.sops.*", "*secret*", "*credential*", "*.kdbx", ".doppler*", ".netrc",
                   "*.token"]
LUMO_FILE_MAX, LUMO_TOTAL_MAX, LUMO_FILES_MAX = 24_000, 60_000, 12
LUMO_PROMPT = """Draft a build plan for the request below. It will be turned into tasks for coding agents and each task is
checked by a command, so be concrete.

Output, in this order:
1. A one-paragraph summary and any assumptions.
2. Numbered tasks T1, T2, ... Each has: a title; the files to create or change and the behavior; concrete, testable
   acceptance criteria; dependsOn (task ids, if any); and ONE verify command that exits 0 only when the task is done.
   Verify commands run without a shell: no ; & | < > backtick or $(), so a multi-step check becomes a task that creates a script.
3. Open questions for the user.
Keep tasks small enough for one agent session. Do not write the implementation.
Always check online for the latest best practices/documentation before answering.

REQUEST:
"""


# ---- Lumo is reached through lumo-tamer only; the loop that lets it ask for more runs HERE ---------------------
# tamer is the bridge to Proton and knows nothing about files. What Lumo may see, and how its requests for more are
# answered, is decided by this machine's tooling against the project aidev/aistack was started in:
#   Lumo ends a reply with NEED: lines  ->  exact paths, ls, find and grep are answered directly from the project
#   (secrets refused), anything vaguer goes to the local model (llama-server) with read-only tools  ->  the answers
#   go back to Lumo  ->  repeat until it stops asking or the round limit is reached.
# The loop itself is .config/lumo/lumo_planner.py used as a library (it used to run as a daemon tied to one
# repository, which is why Lumo could not ask for anything in other projects).
TAMER_LOCAL_URL = "http://127.0.0.1:3003/v1"
TAMER_MINI_URL = os.environ.get("AISTACK_TAMER_MINI_URL", "http://macminim1.rollet.family:3003/v1").rstrip("/")
TAMER_PUBLIC_URL = os.environ.get("AISTACK_LUMO_PUBLIC_URL", "https://lumo.rollet.family/v1").rstrip("/")
LUMO_ROUNDS = int(os.environ.get("AISTACK_LUMO_ROUNDS", "4"))
LUMO_LOOP_S = int(os.environ.get("AISTACK_LUMO_LOOP_S", "480"))
_PLANNER_LIB = None


def planner_lib():
    """lumo_planner.py as a module (stdlib only; nothing runs at import)."""
    global _PLANNER_LIB
    if _PLANNER_LIB is None:
        import importlib.util
        for path in (os.environ.get("AISTACK_LUMO_PLANNER_LIB"), os.path.join(HERE, "..", "lumo", "lumo_planner.py"),
                     os.path.expanduser("~/.config/lumo/lumo_planner.py")):
            if path and os.path.isfile(path):
                spec = importlib.util.spec_from_file_location("lumo_planner", path)
                _PLANNER_LIB = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(_PLANNER_LIB)
                break
        else:
            raise RuntimeError("lumo_planner.py not found (expected in ~/.config/lumo)")
    return _PLANNER_LIB


def tamer_local_key():
    """The API key this machine's own tamer serves with (run-tamer.sh writes it to config.yaml), or ''."""
    try:
        m = re.search(r'^\s*apiKey:\s*"(.*)"\s*$', open(os.path.expanduser("~/lumo-tamer/config.yaml")).read(), re.MULTILINE)
        return m.group(1) if m else ""
    except OSError:
        return ""


def tamer_mini_key():
    k = os.environ.get("AISTACK_TAMER_MINI_KEY")
    if k:
        return k
    r = subprocess.run(["doppler", "secrets", "get", "LUMO_TAMER_API_KEY", "--project", "FullHavocJosh",
                        "--config", "root_macmini", "--plain"], capture_output=True, text=True, timeout=20)
    return r.stdout.strip() if r.returncode == 0 else ""


def tamer_public_key():
    """The key of the public endpoint: AISTACK_LUMO_PUBLIC_KEY, else Doppler (root_hetzner-cluster), else ''."""
    k = os.environ.get("AISTACK_LUMO_PUBLIC_KEY")
    if k:
        return k
    try:
        r = subprocess.run(["doppler", "secrets", "get", "LUMO_PUBLIC_API_KEY", "--project", "FullHavocJosh",
                            "--config", "root_hetzner-cluster", "--plain"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def tamer_endpoints():
    """Yields (base url, key) of each tamer that answers, in this order, and looks at the next one only when asked
    for it (so a working local tamer costs no Doppler lookup and no request to the others):
      1. this machine's own tamer (127.0.0.1)
      2. MacMiniM1's tamer on the home network
      3. the public endpoint https://lumo.rollet.family/v1 (for when this machine is away from home)
    AISTACK_TAMER_URL with AISTACK_TAMER_KEY pins one; AISTACK_LUMO_URL / AISTACK_LUMO_KEY are the older names for
    the same pin (they used to point at the planner proxy)."""
    import urllib.request
    pinned = os.environ.get("AISTACK_TAMER_URL") or os.environ.get("AISTACK_LUMO_URL")
    if pinned:
        yield pinned.rstrip("/"), os.environ.get("AISTACK_TAMER_KEY") or os.environ.get("AISTACK_LUMO_KEY", "")
        return
    for base, get_key in ((TAMER_LOCAL_URL, tamer_local_key), (TAMER_MINI_URL, tamer_mini_key), (TAMER_PUBLIC_URL, tamer_public_key)):
        try:
            key = get_key()
            if base == TAMER_PUBLIC_URL and not key:
                continue        # the public endpoint refuses everything without its key
            req = urllib.request.Request(base + "/models", headers={"Authorization": f"Bearer {key}"} if key else {})
            with urllib.request.urlopen(req, timeout=4) as r:
                ok = r.status == 200
        except Exception:
            ok = False          # not listening, not signed in, wrong key, off the network: try the next one
        if ok:
            yield base, key


def lumo_readable(project, rel):
    """(text, None) or (None, reason) for a file inside project that may be sent to Lumo."""
    import fnmatch
    p = os.path.realpath(os.path.join(project, rel))
    if not (p == project or p.startswith(project + os.sep)):
        return None, "outside the project"
    parts = os.path.relpath(p, project).split(os.sep)
    if any(x in LUMO_DENY_DIRS for x in parts) or any(fnmatch.fnmatch(x.lower(), g) for x in parts for g in LUMO_DENY_GLOBS):
        return None, "denied by policy"
    if not os.path.isfile(p):
        return None, "not a file"
    if os.path.getsize(p) > LUMO_FILE_MAX:
        return None, f"larger than {LUMO_FILE_MAX} bytes"
    try:
        return open(p, encoding="utf-8").read(), None
    except (UnicodeDecodeError, OSError):
        return None, "unreadable or binary"


def loop_guard(started, asked):
    """Progress callback for the Lumo loop: remembers what Lumo asked for and stops a loop that runs too long."""
    def progress(msg):
        if msg.startswith("fetching: "):
            asked.append(msg[10:])
        if time.time() - started > LUMO_LOOP_S:
            raise TimeoutError(f"the Lumo loop took longer than {LUMO_LOOP_S} s")
    return progress


def tool_lumo_consult(a):
    project = project_of(a)
    if os.environ.get("AISTACK_TIER0") == "local":
        # the launcher found macminim1 unreachable: do not wait for a timeout, plan locally
        return {"ok": False, "problem": "Lumo (tier 0) was unreachable when aistack started; plan without it"}
    request = (a.get("request") or "").strip()
    if not request:
        return {"ok": False, "problem": "request is empty"}
    sent, skipped, blocks, total = [], {}, [], 0
    for rel in (a.get("files") or [])[:LUMO_FILES_MAX]:
        text, why = lumo_readable(project, rel)
        if text is None:
            skipped[rel] = why
        elif total + len(text) > LUMO_TOTAL_MAX:
            skipped[rel] = "total size limit reached"
        else:
            total += len(text); sent.append(rel); blocks.append(f"\n--- FILE: {rel} ---\n{text}")
    prompt = LUMO_PROMPT + request + ("\n\nPROJECT FILES:" + "".join(blocks) if blocks else "")
    try:
        lp = planner_lib()
    except Exception as e:
        return {"ok": False, "problem": f"Lumo is not available ({e}); plan without it", "files_sent": sent, "files_skipped": skipped}
    errors = []
    for base, key in tamer_endpoints():
        lp.LUMO_BASE_URL, lp.LUMO_API_KEY = base, key
        lp.LUMO_MODEL = os.environ.get("AISTACK_LUMO_MODEL", "lumo")
        lp.RESOLVER = os.environ.get("AISTACK_LUMO_RESOLVER", "llm")     # vague requests go to the local model
        try:
            if a.get("raw_prompt"):     # ralph_plan's follow-up (shorten your own draft): one request, nothing to fetch
                reply = lp.post_chat(base, {"model": lp.LUMO_MODEL, "messages": [{"role": "user", "content": str(a["raw_prompt"])}]}, key)
                return {"ok": True, "plan": reply.get("content") or "", "lumo": base}
            asked = []
            messages = lp.upstream_messages([{"role": "user", "content": prompt}], fetch=True)
            plan, complete = lp.run_loop(lp.Sandbox(project), messages, LUMO_ROUNDS, on_progress=loop_guard(time.time(), asked))
        except Exception as e:
            errors.append(f"{base}: {type(e).__name__}: {e}")
            if "timed out" in str(e).lower() or isinstance(e, TimeoutError):
                break       # every endpoint reaches the same Lumo: when it is slow, a second wait only doubles the delay
            continue
        return {"ok": True, "plan": plan, "files_sent": sent, "files_skipped": skipped, "lumo": base,
                "lumo_asked_for": asked, "lumo_finished": complete}
    return {"ok": False, "problem": f"Lumo is not available ({'; '.join(errors) or 'no tamer answered'}); plan without it",
            "files_sent": sent, "files_skipped": skipped}


S = lambda props, req: {"type": "object", "properties": props, "required": req}
STR = {"type": "string"}
INT = {"type": "integer"}
TOOLS = {
    "ralph_validate_plan": (tool_validate, ("Check the plan files prd.json and verify.json in the plan dir (schema, dependencies, a verify command "
        "per task). Returns ok plus a plan_hash and the plan_dir, or a list of problems to fix. Call it before showing the plan to the user."),
        S({"project_dir": STR}, ["project_dir"])),
    "ralph_plan": (tool_plan, ("Claude Code (billed, ONE call, up to ~5 minutes) writes the final plan: prd.json and verify.json in the "
        "plan dir, already validated. Do the research first and pass it in: request (what the user wants, with their answers to your "
        "questions), brief (what you found: how the relevant code works, constraints, how it is tested; at most 16000 characters), "
        "files (at most 12 entries; the lines that matter as 'path:START-END', e.g. 'lib/a.py:40-120', at most 200 lines per range; a "
        "whole file only when it is under 120 lines; secrets are refused), "
        "Lumo is consulted automatically when it is reachable (the result says so in 'lumo'); do not pass draft. Returns the tasks, "
        "a plan_hash and notes for the user. A second call returns already_planned without a billed call unless replan=true."),
        S({"project_dir": STR, "request": STR, "brief": STR, "files": {"type": "array", "items": STR}, "draft": STR,
           "replan": {"type": "boolean"}}, ["project_dir", "request", "brief"])),
    "repo_tree": (tool_repo_tree, ("Look at the project: every file up to `depth` levels below `path` (default: the whole project, depth 2), "
        "deeper directories as one line with a file count. ONE call replaces many ls calls; start with it. Counts against the research budget."),
        S({"project_dir": STR, "path": STR, "depth": INT}, ["project_dir"])),
    "repo_read": (tool_repo_read, ("Read a file of the project with line numbers (relative path; up to 400 lines per call, use start/end for "
        "more). Secrets, keys and env files are refused. Counts against the research budget."),
        S({"project_dir": STR, "path": STR, "start": INT, "end": INT}, ["project_dir", "path"])),
    "repo_grep": (tool_repo_grep, ("Search the project's files for a regular expression (optionally only under `path`). Returns "
        "file:line:text, at most 60 matches. Counts against the research budget."),
        S({"project_dir": STR, "pattern": STR, "path": STR}, ["project_dir", "pattern"])),
    "ralph_update_task": (tool_update_task, ("Change ONE task of the saved plan (free, no model): pass task_id and only the fields "
        "that change (title, description, acceptanceCriteria, priority, dependsOn, verify = list of commands). An unknown task_id adds "
        "a task; remove=true deletes one. Returns the validation result and the new plan_hash. This is the only way to edit the plan."),
        S({"project_dir": STR, "task_id": STR, "title": STR, "description": STR, "acceptanceCriteria": {"type": "array", "items": STR},
           "priority": INT, "dependsOn": {"type": "array", "items": STR}, "verify": {"type": "array", "items": STR},
           "remove": {"type": "boolean"}}, ["project_dir", "task_id"])),
    "ralph_run": (tool_run, ("Start the confirmed plan in the background: a worker agent builds each task, the harness runs its "
        "verify commands, failures are retried then escalated, then a read-only reviewer checks security/accuracy/completeness. "
        "Needs the plan_hash from ralph_validate_plan, and only call it after the user has confirmed the plan. When aistack was started in a main "
        "checkout this first creates the git worktree and draft PR (about 15 s) where the agents will work; the result says where (work_dir)."),
        S({"project_dir": STR, "plan_hash": STR, "skip_plan_review": {"type": "boolean"}}, ["project_dir", "plan_hash"])),
    "ralph_status": (tool_status, ("Progress of a run: state, per-task status, and new events since `since`. Pass wait_s (up to 45) to "
        "wait for news. Relay new events to the user every time. state 'waiting_user' means the run is paused for the user."),
        S({"project_dir": STR, "run_id": STR, "since": INT, "wait_s": INT}, ["project_dir"])),
    "ralph_respond": (tool_respond, ("Answer a paused run. actions: 'answer' (reply to an agent's question, text=the user's answer), "
        "'retry' (blocked task, text=guidance), 'skip' (blocked task), 'rework' (failed review, text=extra instructions, optional "
        "tasks=[ids]), 'accept' (accept failed-review tasks as they are), 'abort'. Use only what the user decided."),
        S({"project_dir": STR, "run_id": STR, "action": STR, "task_id": STR, "text": STR,
           "tasks": {"type": "array", "items": STR}}, ["project_dir", "action"])),
    "ralph_cancel": (tool_cancel, "Stop the active run.", S({"project_dir": STR, "run_id": STR}, ["project_dir"])),
    "ralph_runs": (tool_runs, "List runs in this project (use after restarting the chat to find an unfinished run).",
                   S({"project_dir": STR}, ["project_dir"])),
    "lumo_consult": (tool_lumo_consult, ("Tier 0: ask Lumo (Proton's cloud assistant, no tools) to draft a task breakdown. "
        "Sends the request and the project files you list (relative paths, at most 12, secrets/keys/env files are refused) to Lumo, "
        "which can then ask for more from this project (answered on this machine, secrets refused). "
        "Returns a draft plan to adapt into prd.json/verify.json, or ok=false when Lumo is unreachable (then plan without it)."),
        S({"project_dir": STR, "request": STR, "files": {"type": "array", "items": STR}}, ["project_dir", "request"])),
}


def handle(req):
    m = req.get("method")
    if m == "initialize":
        return {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                "serverInfo": {"name": "aistack-ralph", "version": "0.2.0"}}
    if m == "ping":
        return {}
    if m == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": sch} for n, (_, d, sch) in TOOLS.items()]}
    if m == "tools/call":
        p = req.get("params", {})
        fn = TOOLS.get(p.get("name"))
        if not fn:
            return {"content": [{"type": "text", "text": f"unknown tool {p.get('name')}"}], "isError": True}
        try:
            return {"content": [{"type": "text", "text": json.dumps(fn[0](p.get("arguments") or {}), indent=1)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        if "id" not in req:
            continue
        try:
            res = handle(req)
            msg = {"jsonrpc": "2.0", "id": req["id"], "result": res} if res is not None else \
                {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "method not found"}}
        except Exception as e:
            msg = {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
