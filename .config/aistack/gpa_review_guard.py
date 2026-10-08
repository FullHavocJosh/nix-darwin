#!/usr/bin/env python3
"""Deterministic guardrails for gpa's AI code review (.zshrc_functions_git calls this; stdlib only).

The review model is small and its findings used to block a commit as they came: invented text, pre-existing code,
style opinions marked Critical, and a new set on every run. This decides, without a model, which findings may block.

  guard   stdin {"issues": [...], "waive": [fingerprints]}  ->  {"blocking", "advisory", "dropped", "waived"}
  settle  stdin {"blocking": [...]}                          ->  records the round in <git dir>/gpa_review_state.json

A finding may block only when ALL of these hold:
  1. evidence: it quotes an added line of the staged diff of the file it names (checked here, whitespace-insensitive).
     No evidence, or evidence that is not an added line, means the finding is dropped. That removes invented findings
     and findings about code the change did not touch.
  2. it is Critical and its category is one of BLOCKING. Everything else is advisory: printed, never blocking.
  3. its line was not already reviewed in an earlier round of this same change. A re-run after a fix only gets to
     block on lines that are new since the last round, so the model cannot re-roll lines it already passed.
  4. it has no waiver (gpa --waive <fingerprint> --reason ..., people only; recorded in the commit message).
gpa then asks the model to confirm each remaining finding against the code around its line before it blocks.
Blocking findings from the previous round are carried over while their line is still in the diff, so a finding
cannot disappear just because the model did not repeat it.

State is per git dir (so per worktree) and is reset when HEAD changes, which is what a commit does.
"""
import hashlib
import json
import os
import subprocess
import sys

BLOCKING = {"secret-exposure", "injection", "destructive-command", "broken-syntax", "auth-bypass"}
EVIDENCE_MIN = 8
CONTEXT_LINES = 12


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else ""


def norm(s):
    return " ".join(str(s).split())


def staged_files():
    return [f for f in git("diff", "--cached", "--name-only").splitlines() if f]


def added_lines(path):
    """Normalized text of every added line in the staged diff of one file."""
    out = []
    for ln in git("diff", "--cached", "-U0", "--", path).splitlines():
        if ln.startswith("+") and not ln.startswith("+++"):
            n = norm(ln[1:])
            if n:
                out.append(n)
    return out


def match_line(evidence, lines):
    """The added line the evidence quotes, or None. The model may quote part of a line, or prefix it with '+'."""
    ev = norm(str(evidence).lstrip("+"))
    if len(ev) < EVIDENCE_MIN:
        return None
    for ln in lines:
        if ev in ln or (len(ln) >= EVIDENCE_MIN and ln in ev):
            return ln
    return None


def line_id(path, line):
    return hashlib.sha1(f"{path}\0{line}".encode()).hexdigest()[:16]


def fingerprint(path, line, category):
    return hashlib.sha1(f"{path}\0{line}\0{category}".encode()).hexdigest()[:10]


def context(path, line):
    """The staged file around the quoted line, for the confirmation pass."""
    src = git("show", f":{path}").splitlines()
    for i, ln in enumerate(src):
        if norm(ln) == line:
            lo, hi = max(i - CONTEXT_LINES, 0), min(i + CONTEXT_LINES + 1, len(src))
            return "\n".join(f"{n + 1}{'>' if n == i else ' '} {src[n]}" for n in range(lo, hi))
    return ""


def state_path():
    return os.path.join(git("rev-parse", "--absolute-git-dir").strip() or ".git", "gpa_review_state.json")


def load_state():
    head = git("rev-parse", "HEAD").strip()
    try:
        with open(state_path()) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {}
    if st.get("head") != head:
        st = {"head": head, "round": 0, "reviewed": [], "blocking": {}}
    return st


def guard(inp):
    st = load_state()
    reviewed, waive = set(st["reviewed"]), set(inp.get("waive") or [])
    staged = set(staged_files())
    lines_of = {}
    out = {"blocking": [], "advisory": [], "dropped": [], "waived": [], "round": st["round"] + 1}
    seen = set()

    def lines(path):
        if path not in lines_of:
            lines_of[path] = added_lines(path)
        return lines_of[path]

    for it in inp.get("issues") or []:
        if not isinstance(it, dict) or not it.get("file"):
            out["dropped"].append({"file": "?", "issue": str(it)[:120], "why": "not a finding object"})
            continue
        path = str(it["file"])
        brief = {"file": path, "severity": it.get("severity"), "issue": it.get("issue"), "recommendation": it.get("recommendation")}
        if path not in staged:
            out["dropped"].append(dict(brief, why="names a file that is not in the staged changes"))
            continue
        line = match_line(it.get("evidence", ""), lines(path))
        if not line:
            out["dropped"].append(dict(brief, why="its evidence is not an added line of this file's staged diff"))
            continue
        category = str(it.get("category", "")).strip().lower()
        fp = fingerprint(path, line, category)
        if fp in seen:
            continue
        seen.add(fp)
        item = dict(brief, category=category, evidence=line, fingerprint=fp)
        if it.get("severity") != "Critical" or category not in BLOCKING:
            out["advisory"].append(dict(item, why="not a blocking category"))
        elif fp in waive:
            out["waived"].append(item)
        elif line_id(path, line) in reviewed and fp not in st["blocking"]:
            out["advisory"].append(dict(item, why="this line already passed an earlier review round"))
        else:
            out["blocking"].append(dict(item, context=context(path, line)))
    # findings that blocked last round stay until their line is gone, they are waived, or confirmation rejects them
    for fp, item in st["blocking"].items():
        if fp in seen:
            continue
        path, line = item.get("file", ""), item.get("evidence", "")
        if path in staged and line in lines(path):
            if fp in waive:
                out["waived"].append(item)
            else:
                out["blocking"].append(dict(item, carried=True, context=context(path, line)))
    return out


def settle(inp):
    st = load_state()
    reviewed = set(st["reviewed"])
    for path in staged_files():
        reviewed.update(line_id(path, ln) for ln in added_lines(path))
    keep = ("file", "severity", "issue", "recommendation", "category", "evidence", "fingerprint")
    st.update(round=st["round"] + 1, reviewed=sorted(reviewed),
              blocking={b["fingerprint"]: {k: b.get(k) for k in keep} for b in inp.get("blocking") or [] if b.get("fingerprint")})
    with open(state_path(), "w") as f:
        json.dump(st, f)
    return {"round": st["round"], "reviewed_lines": len(reviewed), "blocking": len(st["blocking"])}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("guard", "settle"):
        print("usage: gpa_review_guard.py guard|settle  (JSON on stdin)", file=sys.stderr)
        return 2
    try:
        inp = json.loads(sys.stdin.read() or "{}")
    except ValueError as e:
        print(f"invalid JSON on stdin: {e}", file=sys.stderr)
        return 2
    print(json.dumps(guard(inp) if cmd == "guard" else settle(inp)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
