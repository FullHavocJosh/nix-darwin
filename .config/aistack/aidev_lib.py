"""Plan, worktree and Lumo endpoint helpers shared by aidev on tuios, ainfo and lumo_mcp. Taken unchanged from the
retired ralph_mcp module; stdlib only, nothing runs at import."""

import hashlib
import json
import os
import re
import shlex
import subprocess
import time


def needs_shell(cmd):
    """True when a verify command only works in a shell. The driver runs verify commands with shlex.split and no
    shell, so an operator inside quotes is plain text (python3 -c "import sys; sys.exit(0)" is fine) while an unquoted
    ; & | < > ( ), a backtick or $( would be passed to the program as an argument and never do what was meant."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:  # unbalanced quotes
        return True
    return any(
        t and (set(t) <= set("();<>|&") or t.startswith(("$(", "`"))) for t in tokens
    )


def rj(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


# aidev on tuios points each run at its own plan dir and worktree record (load_lib sets these on its instance)
PLAN_DIR = os.environ.get("AISTACK_PLAN_DIR") or None
PROJECT_META = os.environ.get("AISTACK_PROJECT_META") or None


def state_dir(project):
    """Where aistack keeps everything for this project, outside the repository."""
    d = os.environ.get("AISTACK_STATE_DIR")
    if d:
        return os.path.realpath(os.path.expanduser(d))
    home = os.environ.get("AISTACK_HOME") or os.path.join(os.path.expanduser(os.environ.get("AI_HOME") or "~/.ai"), "aidev")
    return os.path.join(
        home,
        f"{os.path.basename(project)}-{hashlib.sha1(project.encode()).hexdigest()[:10]}",
    )


def plan_dir(project):
    return PLAN_DIR or os.path.join(state_dir(project), "plan")


def meta_path(project):
    """project.json: the work dir, branch and PR of the current plan."""
    return PROJECT_META or os.path.join(state_dir(project), "project.json")


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
    if "title" in prd and not (
        isinstance(prd["title"], str)
        and prd["title"].strip()
        and len(prd["title"]) <= 100
    ):
        problems.append(
            "prd.json: 'title' (the pull request title: imperative, no 'feat:' prefix) must be a non-empty string of at most 100 characters"
        )
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
        if (
            not isinstance(ac, list)
            or not ac
            or not all(isinstance(x, str) and x.strip() for x in ac)
        ):
            problems.append(
                f"{tid}: 'acceptanceCriteria' must be a non-empty list of strings"
            )
        if not isinstance(s.get("priority"), (int, float)):
            problems.append(f"{tid}: 'priority' must be a number (1 = first)")
        if s.get("passes") is not False:
            problems.append(f"{tid}: 'passes' must be false")
        for d in s.get("dependsOn", []) or []:
            if d not in ids:
                problems.append(f"{tid}: dependsOn {d!r} is not a task id")
    # cycles
    deps = {
        s["id"]: list(s.get("dependsOn", []) or [])
        for s in stories
        if isinstance(s, dict) and "id" in s
    }
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
        problems.append(
            "Missing or invalid verify.json in the plan dir (object mapping task id -> list of commands)"
        )
        return problems
    for tid in deps:
        cmds = verify.get(tid)
        if isinstance(cmds, str):
            cmds = [cmds]
        if not cmds or not all(isinstance(c, str) and c.strip() for c in cmds):
            problems.append(
                f"verify.json: task {tid} needs at least one verify command (an exit-0-on-success shell-free command)"
            )
            continue
        for c in cmds:
            if needs_shell(c):
                problems.append(
                    f"verify.json: {tid}: no shell syntax (; & | < > ` $()) in '{c}'. Verify commands run without a shell. "
                    "Use one plain command (operators inside quotes are fine), or have a task create a check script and run that. "
                    "Never point a verify command at a file that no task creates."
                )
    for tid in verify:
        if tid not in deps:
            problems.append(f"verify.json: {tid} is not a task id")
    return problems


def present_plan(prd, verify, notes=(), lines=()):
    """The plan as text for the user. The chat agent prints this as it is: when a small model summarized the plan
    itself it left out the acceptance criteria and verify commands and added options of its own."""
    out = [
        f"PLAN: {prd.get('title') or prd.get('name')}",
        str(prd.get("description") or "").strip(),
        "",
    ]
    for s in sorted(prd.get("userStories", []), key=lambda s: s.get("priority", 0)):
        out.append(
            f"{s['id']}  {s.get('title', '')}"
            + (f"   (after {', '.join(s['dependsOn'])})" if s.get("dependsOn") else "")
        )
        out.append(f"    does:   {str(s.get('description', '')).strip()}")
        out += [f"    done when: {c}" for c in s.get("acceptanceCriteria", [])]
        out += [f"    verify: {c}" for c in verify.get(s["id"], [])]
    if notes:
        out += ["", "NOTES FROM CLAUDE:"] + [f"  - {n}" for n in notes]
    out += [""] + [x for x in lines if x]
    out.append("Next: say what to change, or say 'start' to build this plan.")
    return "\n".join(out)


def save_plan_text(project, text):
    path = os.path.join(plan_dir(project), "PLAN.txt")
    with open(path, "w") as f:
        f.write(text + "\n")
    return path


# gpr's AI interface: --auto never prompts, --title/--description become the PR title and body, the last stdout line is
# JSON ({"ok","branch","worktree","pr_url","pr_number"}); AISTACK_BRANCH / _PR_TYPE / _PR_TITLE / _PR_BODY are set below
DEFAULT_WORKTREE_CMD = (
    "source ~/.zshrc_functions_git 2>/dev/null; source ~/.zshrc_functions_ai 2>/dev/null; "
    'gpr_func --auto "$AISTACK_PR_TYPE" "$AISTACK_BRANCH" --title "$AISTACK_PR_TITLE" '
    '--description "$AISTACK_PR_BODY"'
)


def pr_title_and_body(prd, verify):
    """The draft PR's title and description, from the plan: prd.json 'title' (falls back to 'name'), its description,
    the tasks with acceptance criteria and verify commands, and which tiers do the work."""
    ptype = prd.get("type") or "feat"
    text = str(prd.get("title") or prd.get("name") or "aistack plan").strip()
    text = re.sub(r"^(feat|fix)(\([^)]*\))?:\s*", "", text, flags=re.IGNORECASE)
    title = f"{ptype}: {text}"
    if len(title) > 72:
        title = title[:71].rstrip() + "\u2026"
    lines = [
        "## Summary",
        str(prd.get("description") or prd.get("name") or "").strip(),
        "",
        "## Plan",
    ]
    for st in prd.get("userStories", []):
        crit = "; ".join(st.get("acceptanceCriteria", []))
        v = verify.get(st["id"], []) if isinstance(verify, dict) else []
        v = [v] if isinstance(v, str) else v
        lines.append(
            f"- **{st['id']}** {st.get('title', '')}"
            + (f": {crit}" if crit else "")
            + (" (verify: " + ", ".join(f"`{c}`" for c in v) + ")" if v else "")
        )
    lines += [
        "",
        "---",
        "Opened by aistack when the plan was confirmed. "
        + (
            os.environ.get("AISTACK_TIERS", "") + ". "
            if os.environ.get("AISTACK_TIERS")
            else ""
        )
        + "Changes stay uncommitted in this worktree until committed with gpc/gpa.",
    ]
    return ptype, title, "\n".join(lines)


def ensure_workdir(project, prd, verify=None):
    """Where the agents work. In a main checkout (AISTACK_WORKTREE_MODE=create) the first confirmed plan creates a gpr
    worktree + draft PR, later runs reuse it while it exists. Elsewhere the project itself is the work dir."""
    meta_p = meta_path(project)
    meta = rj(meta_p, {})
    if meta.get("work_dir") and os.path.isdir(meta["work_dir"]):
        return meta["work_dir"], False, None
    if os.environ.get("AISTACK_WORKTREE_MODE") != "create":
        return project, False, None
    slug = (
        re.sub(
            r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(prd.get("name", "plan")).lower())
        ).strip("-")[:28]
        or "plan"
    )
    branch = f"aistack-{slug}-{time.strftime('%H%M')}"
    ptype, title, body = pr_title_and_body(prd, verify or {})
    env = dict(
        os.environ,
        AISTACK_BRANCH=branch,
        AISTACK_PR_TYPE=ptype,
        AISTACK_PR_TITLE=title,
        AISTACK_PR_BODY=body,
    )
    cmd = os.environ.get("AISTACK_WORKTREE_CMD")
    argv = ["/bin/sh", "-c", cmd] if cmd else ["zsh", "-c", DEFAULT_WORKTREE_CMD]
    try:
        r = subprocess.run(
            argv,
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            timeout=170,
            stdin=subprocess.DEVNULL,
        )
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
        return (
            None,
            False,
            f"creating the worktree {wd} failed (exit {r.returncode}): {tail}",
        )
    meta.update(
        work_dir=wd,
        branch=branch,
        source_dir=project,
        created=time.strftime("%Y-%m-%dT%H:%M:%S"),
        pr_url=result.get("pr_url"),
        pr_number=result.get("pr_number"),
        pr_title=title,
    )
    os.makedirs(os.path.dirname(meta_p), exist_ok=True)
    json.dump(meta, open(meta_p, "w"), indent=2)
    return wd, True, None


TAMER_LOCAL_URL = "http://127.0.0.1:3003/v1"
TAMER_MINI_URL = os.environ.get(
    "AISTACK_TAMER_MINI_URL", "http://macminim1.rollet.family:3003/v1"
).rstrip("/")
TAMER_PUBLIC_URL = os.environ.get(
    "AISTACK_LUMO_PUBLIC_URL", "https://lumo.rollet.family/v1"
).rstrip("/")
def tamer_local_key():
    """The API key this machine's own tamer serves with (run-tamer.sh writes it to config.yaml), or ''."""
    try:
        m = re.search(
            r'^\s*apiKey:\s*"(.*)"\s*$',
            open(os.path.expanduser("~/lumo-tamer-fullhavoc/config.yaml")).read(),
            re.MULTILINE,
        )
        return m.group(1) if m else ""
    except OSError:
        return ""


def tamer_mini_key():
    k = os.environ.get("AISTACK_TAMER_MINI_KEY")
    if k:
        return k
    r = subprocess.run(
        [
            "doppler",
            "secrets",
            "get",
            "LUMO_TAMER_API_KEY",
            "--project",
            "FullHavocJosh",
            "--config",
            "root_macmini",
            "--plain",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return r.stdout.strip() if r.returncode == 0 else ""


def tamer_public_key():
    """The key of the public endpoint: AISTACK_LUMO_PUBLIC_KEY, else Doppler (root_hetzner-cluster), else ''."""
    k = os.environ.get("AISTACK_LUMO_PUBLIC_KEY")
    if k:
        return k
    try:
        r = subprocess.run(
            [
                "doppler",
                "secrets",
                "get",
                "LUMO_PUBLIC_API_KEY",
                "--project",
                "FullHavocJosh",
                "--config",
                "root_hetzner-cluster",
                "--plain",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
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
        yield (
            pinned.rstrip("/"),
            os.environ.get("AISTACK_TAMER_KEY")
            or os.environ.get("AISTACK_LUMO_KEY", ""),
        )
        return
    for base, get_key in (
        (TAMER_LOCAL_URL, tamer_local_key),
        (TAMER_MINI_URL, tamer_mini_key),
        (TAMER_PUBLIC_URL, tamer_public_key),
    ):
        try:
            key = get_key()
            if base == TAMER_PUBLIC_URL and not key:
                continue  # the public endpoint refuses everything without its key
            req = urllib.request.Request(
                base + "/models",
                headers={"Authorization": f"Bearer {key}"} if key else {},
            )
            with urllib.request.urlopen(req, timeout=4) as r:
                ok = r.status == 200
        except Exception:
            ok = False  # not listening, not signed in, wrong key, off the network: try the next one
        if ok:
            yield base, key
