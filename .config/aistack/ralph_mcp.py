#!/usr/bin/env python3
"""MCP bridge (stdio, JSON-RPC 2.0) between a chat agent (pi) and the aistack run driver.

Tools: ralph_validate_plan, ralph_review_plan (tier 2 plan review), ralph_plan (aidev: Claude writes the plan), ralph_run, ralph_status, ralph_respond, ralph_cancel, ralph_runs, lumo_consult (tier 0).
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
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
ROOTS = [os.path.realpath(p) for p in os.environ.get("RALPH_MCP_ROOTS", "").split(":") if p]
PROTOCOL = "2024-11-05"
SHELLISH = re.compile(r"[;&|<>`]|\$\(")


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
            if SHELLISH.search(c):
                problems.append(f"verify.json: {tid}: no shell syntax (; & | < > ` $()) in '{c}'. Put complex checks in a script file and run that, e.g. 'python3 checks/check_{tid}.py'")
    for tid in verify:
        if tid not in deps:
            problems.append(f"verify.json: {tid} is not a task id")
    return problems


def tool_validate(a):
    project = project_of(a)
    prd, verify, h = load_plan(project)
    problems = validate(prd, verify)
    if problems:
        return {"ok": False, "problems": problems, "plan_dir": plan_dir(project)}
    tasks = [{"id": s["id"], "title": s["title"], "priority": s["priority"], "dependsOn": s.get("dependsOn", []),
              "verify": verify[s["id"]]} for s in prd["userStories"]]
    return {"ok": True, "plan_hash": h, "name": prd["name"], "tasks": tasks, "plan_dir": plan_dir(project),
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


PLAN_REVIEW_PROMPT = """You are the tier 2 reviewer in aistack. A weaker planner (a small local model, with a cloud assistant's draft)
wrote the build plan below. It has NOT been built yet. Catch what they missed, before anything is implemented.
Read the project in the current directory (read-only; Read, Grep, Glob, git status/diff/log) to check the plan against the real code.
Judge: (1) accuracy: do the named files, functions and behaviors exist and match the code; (2) completeness: requirements or edge cases
not covered, missing tasks, wrong dependsOn order; (3) task size: each task should fit one agent session; (4) verify commands: each must
exit 0 only when its task is really done, and must not pass on unrelated or empty state; (5) security and risky defaults.
Do NOT modify any file. Do NOT review code quality of code that does not exist yet.
Reply in this form: FIRST line exactly 'Verdict: PASS' or 'Verdict: FAIL' (FAIL when the plan must change before building),
then findings, most serious first, each naming the task id and the concrete fix. Be concise.

USER REQUEST / PLAN DESCRIPTION: %s

prd.json:
%s

verify.json:
%s
"""


def plan_review_path(project):
    return os.path.join(state_dir(project), "plan-review.json")


def tool_review_plan(a):
    """Tier 2 reviews the confirmed-by-validation plan BEFORE the user is asked to confirm it for building."""
    project = project_of(a)
    prd, verify, h = load_plan(project)
    problems = validate(prd, verify)
    if problems:
        return {"ok": False, "problems": problems, "problem": "fix the plan and call ralph_validate_plan first"}
    prev = rj(plan_review_path(project), {})
    if prev.get("verdict") and not a.get("force"):
        return {"ok": True, "already_reviewed": True, "verdict": prev.get("verdict"), "plan_hash": h, "report": prev.get("report"), "billed_calls": 0,
                "next": "Only the first plan is reviewed; later edits are not re-reviewed. Do not call ralph_review_plan again. "
                        "Show the user the plan and, once they confirm, call ralph_run with the plan_hash."}
    prompt = PLAN_REVIEW_PROMPT % (str(prd.get("description") or prd.get("name") or ""),
                                   json.dumps(prd, indent=1), json.dumps(verify, indent=1))
    cmd = os.environ.get("AISTACK_PLAN_REVIEW_CMD")
    argv = ["/bin/sh", "-c", cmd] if cmd else [os.path.join(HERE, "claude-review.sh"), "-p", prompt]
    env = dict(os.environ, AISTACK_WORKDIR=project, AISTACK_PLAN_REVIEW_PROMPT=prompt)
    env.pop("AISTACK_REVIEWS_DIR", None)    # stdout only: the reviewer is not allowed to write anything
    try:
        r = subprocess.run(argv, cwd=project, env=env, capture_output=True, text=True, timeout=int(os.environ.get("AISTACK_PLAN_REVIEW_TIMEOUT_S", "170")),
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "problem": f"the plan review (Claude Code) did not finish: {type(e).__name__}: {e}"}
    text = (r.stdout or "").strip()
    first = text.splitlines()[0].strip() if text else ""
    m = re.match(r"(?i)^\**\s*verdict:\s*(pass|fail)", first)
    if r.returncode != 0 or not m:
        return {"ok": False, "problem": f"the plan review produced no valid verdict (exit {r.returncode})", "tail": (text or r.stderr or "")[-600:]}
    verdict = m.group(1).upper()
    os.makedirs(os.path.join(state_dir(project), "reviews"), exist_ok=True)
    report = os.path.join(state_dir(project), "reviews", "plan-review.md")
    with open(report, "w") as f:
        f.write(text + "\n")
    json.dump({"plan_hash": h, "name": prd["name"], "verdict": verdict, "report": report, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, open(plan_review_path(project), "w"))
    return {"ok": True, "verdict": verdict, "plan_hash": h, "report": report, "findings": text[:6000], "billed_calls": 1,
            "next": "Show the findings to the user. If you change the plan, call ralph_validate_plan again, not ralph_review_plan "
                    "(only the first plan is reviewed; edits made after this review are not re-reviewed). Only after the user confirms the reviewed plan, call ralph_run with the plan_hash."}


# ---- aidev: Claude Code writes the plan (one billed call) instead of reviewing one -------------------------------
# The chat agent (the local model) does the research for free and passes it in: a brief, the files that matter
# (inlined here, so the local model does not have to copy code through its own output), and Lumo's draft if any.
# Claude returns the finished prd.json + verify.json; nothing has to apply review findings afterwards.
PLAN_BRIEF_MAX, PLAN_DRAFT_MAX = 16_000, 12_000
PLAN_PROMPT = """You write the build plan for a coding run. Cheaper agents build it: a free coding model implements one task per
session, a harness counts a task as done only when that task's verify commands exit 0, and you review the whole result once at the end.
A plan that is vague or has weak verify commands costs failed attempts, so be exact.

Below: the user's request, a research brief written by a small local model (it can be wrong or incomplete), the project files it
picked, and possibly a draft plan from another assistant (treat it as a draft, keep only what fits the code).
Everything you need should be below. Use Read, Grep and Glob in the current directory ONLY to close a specific gap or to check a
claim the plan depends on. Do not explore, and do not modify anything.

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

USER REQUEST:
%s

RESEARCH BRIEF:
%s
%s%s"""


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
    brief, draft = (a.get("brief") or "").strip(), (a.get("draft") or "").strip()
    truncated = [n for n, t, cap in (("brief", brief, PLAN_BRIEF_MAX), ("draft", draft, PLAN_DRAFT_MAX)) if len(t) > cap]
    brief, draft = brief[:PLAN_BRIEF_MAX], draft[:PLAN_DRAFT_MAX]
    sent, skipped, blocks, total = [], {}, [], 0
    for spec in (a.get("files") or [])[:LUMO_FILES_MAX]:
        _, text, why = plan_file(project, str(spec))
        if text is None:
            skipped[spec] = why
        elif total + len(text) > LUMO_TOTAL_MAX:
            skipped[spec] = "total size limit reached"
        else:
            total += len(text); sent.append(spec); blocks.append(f"\n--- FILE: {spec} ---\n{text}")
    prompt = PLAN_PROMPT % (request, brief or "(none)",
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
    out = {"ok": not problems, "plan_hash": h, "plan_dir": plan_dir(project), "notes": notes, "files_sent": sent,
           "files_skipped": skipped, "truncated": truncated, "billed_calls": 1}
    if problems:
        out.update(problems=problems, next="Claude's plan is saved but has the problems listed. Fix them yourself in prd.json / "
                   "verify.json in the plan dir, then call ralph_validate_plan. Do not call ralph_plan again (it is billed).")
        return out
    out.update(name=prd["name"], tasks=[{"id": s["id"], "title": s["title"], "priority": s["priority"],
                                        "dependsOn": s.get("dependsOn", []), "verify": verify[s["id"]]} for s in prd["userStories"]],
               next="Show the user the plan and the notes. If they want changes, edit the plan files yourself and call "
                    "ralph_validate_plan. Only after they confirm, call ralph_run with the current plan_hash.")
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
            return {"started": False, "problem": "Claude Code has not reviewed this plan yet. Call ralph_review_plan, show the user "
                    "the findings, and get their confirmation of the reviewed plan. Pass skip_plan_review=true only if the user explicitly "
                    "said to skip the review (it is billed)."}
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


def lumo_key():
    k = os.environ.get("AISTACK_LUMO_KEY")
    if k:
        return k
    r = subprocess.run(["doppler", "secrets", "get", "LUMO_PLANNER_API_KEY", "--project", "FullHavocJosh",
                        "--config", "root_macmini", "--plain"], capture_output=True, text=True, timeout=20)
    return r.stdout.strip() if r.returncode == 0 else ""


# this machine's own planner proxy, and the always-on LAN host's (AISTACK_LUMO_MINI_URL moves the latter)
LUMO_LOCAL_URL = "http://127.0.0.1:8765/v1"
LUMO_MINI_URL = os.environ.get("AISTACK_LUMO_MINI_URL", "http://macminim1.rollet.family:8765/v1").rstrip("/")


def lumo_local_key():
    """This device's own planner key (lumo-common.sh keeps a copy of the Doppler value here), or ''."""
    try:
        return open(os.environ.get("LUMO_PLANNER_KEY_FILE") or os.path.expanduser("~/.lumo-planner-key")).read().strip()
    except OSError:
        return ""


def lumo_endpoints():
    """[(base url, key getter)] to try in order. AISTACK_LUMO_URL pins one. Otherwise this machine's own planner proxy
    comes first when it answers (loopback only, this device's key: nix-modules/macos/lumo.nix), then the one on
    MacMiniM1 with the Mini's key. The two devices have different keys."""
    import urllib.request
    pinned = os.environ.get("AISTACK_LUMO_URL")
    if pinned:
        return [(pinned.rstrip("/"), lumo_key)]
    out = []
    try:
        k = lumo_local_key()
        req = urllib.request.Request(LUMO_LOCAL_URL + "/models", headers={"Authorization": f"Bearer {k}"} if k else {})
        with urllib.request.urlopen(req, timeout=2) as r:
            if r.status == 200:
                out.append((LUMO_LOCAL_URL, lumo_local_key))
    except Exception:
        pass
    return out + [(LUMO_MINI_URL, lumo_key)]


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


def tool_lumo_consult(a):
    import urllib.request
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
    body = json.dumps({"model": "lumo-planner", "messages": [{"role": "user", "content": prompt}]}).encode()
    errors = []
    for base, get_key in lumo_endpoints():
        headers = {"Content-Type": "application/json", "X-Lumo-No-Fetch": "1"}
        key = get_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        try:
            with urllib.request.urlopen(urllib.request.Request(base + "/chat/completions", body, headers), timeout=180) as r:
                plan = json.load(r)["choices"][0]["message"]["content"]
        except Exception as e:
            errors.append(f"{base}: {type(e).__name__}: {e}")
            continue
        return {"ok": True, "plan": plan, "files_sent": sent, "files_skipped": skipped, "lumo": base}
    return {"ok": False, "problem": f"Lumo is not available ({'; '.join(errors)}); plan without it",
            "files_sent": sent, "files_skipped": skipped}


S = lambda props, req: {"type": "object", "properties": props, "required": req}
STR = {"type": "string"}
INT = {"type": "integer"}
TOOLS = {
    "ralph_validate_plan": (tool_validate, ("Check the plan files prd.json and verify.json in the plan dir (schema, dependencies, a verify command "
        "per task). Returns ok plus a plan_hash and the plan_dir, or a list of problems to fix. Call it before showing the plan to the user."),
        S({"project_dir": STR}, ["project_dir"])),
    "ralph_review_plan": (tool_review_plan, ("Tier 2: Claude Code (read-only, billed, one call, up to ~3 minutes) reviews the validated plan against the "
        "real code BEFORE building, to catch what the planner and Lumo missed. Returns Verdict PASS or FAIL and findings. Call it after "
        "ralph_validate_plan and the user's first confirmation; ralph_run refuses a plan that has no review. Only the first plan is reviewed: once a review exists for the plan, "
        "later calls return already_reviewed without a billed call unless force=true."),
        S({"project_dir": STR, "force": {"type": "boolean"}}, ["project_dir"])),
    "ralph_plan": (tool_plan, ("Claude Code (billed, ONE call, up to ~5 minutes) writes the final plan: prd.json and verify.json in the "
        "plan dir, already validated. Do the research first and pass it in: request (what the user wants, with their answers to your "
        "questions), brief (what you found: how the relevant code works, constraints, how it is tested; at most 16000 characters), "
        "files (relative paths that matter, at most 12; add a line range for a big file, e.g. 'lib/a.py:40-120'; secrets are refused), "
        "and draft (Lumo's draft, if you have one). Returns the tasks, a plan_hash and notes for the user. A second call returns "
        "already_planned without a billed call unless replan=true."),
        S({"project_dir": STR, "request": STR, "brief": STR, "files": {"type": "array", "items": STR}, "draft": STR,
           "replan": {"type": "boolean"}}, ["project_dir", "request", "brief"])),
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
        "Sends the request and the project files you list (relative paths, at most 12, secrets/keys/env files are refused) to Lumo. "
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
