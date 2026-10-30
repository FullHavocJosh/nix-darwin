"""The 9B reviews a work dir's diff file by file for the plan pane."""

import os
import subprocess

SYSTEM = (
    "You review one file's diff for a planner. List only real problems: bugs, "
    "security holes, missing edge cases. One line each: 'line N: problem'. "
    "If there are none, reply exactly: no findings."
)


def _git(work_dir, *args):
    return subprocess.run(
        ["git", "-C", work_dir, *args], capture_output=True, text=True
    ).stdout


def changed_files(work_dir):
    tracked = _git(work_dir, "diff", "--name-only", "HEAD").splitlines()
    new = _git(work_dir, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({p for p in tracked + new if p})


def file_diff(work_dir, path, max_chars=12000):
    tracked = _git(work_dir, "ls-files", "--", path).strip()
    if tracked:
        text = _git(work_dir, "diff", "HEAD", "--", path)
    else:
        try:
            with open(os.path.join(work_dir, path), errors="replace") as f:
                text = "".join("+" + line for line in f.read().splitlines(True))
        except OSError:
            text = ""
    return text[:max_chars]


def review(work_dir, paths, ask, max_chars=1500):
    if not paths:
        paths = changed_files(work_dir)
    out = []
    size = 0
    for i, path in enumerate(paths):
        if size > max_chars:
            out.append("not reviewed (size cap): " + ", ".join(paths[i:]))
            break
        try:
            reply = ask(file_diff(work_dir, path), SYSTEM)
        except RuntimeError as e:
            entry = f"### {path}: not reviewed ({e})"
        else:
            if reply.strip().lower() == "no findings":
                entry = f"### {path}: no findings"
            else:
                entry = f"### {path}\n{reply[:400]}"
        out.append(entry)
        size += len(entry) + 1
    stat = _git(work_dir, "diff", "--stat", "HEAD")
    return "\n".join(out) + "\n\n" + stat
