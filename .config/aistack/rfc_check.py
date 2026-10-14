#!/usr/bin/env python3
"""Gate significant aidev changes on an approved or implemented RFC (.config/aistack; stdlib only).

A significant file is a .py file directly in .config/aistack/ (not in a subdirectory) or planner-prompt.md. A change to
a significant file must be covered by an RFC whose frontmatter status is approved or implemented and whose `touches`
lists that exact path. Tests, docs, the template and the rfcs/ directory itself never gate anything.

  rfc_check.py [--rfc-dir DIR] [--base REF] [--changed PATH ...]

The default rfc dir is rfcs/ next to this script. Without --changed the changed paths come from
`git diff --name-only <base>...HEAD` (base defaults to main), run in the git root of this script's directory.

Exit 0 when every significant path is covered (or there are none): "rfc_check: ok".
Exit 1 when some significant path is not covered: one "RFC required: <path>" line plus a pointer to the template.
Exit 2 when an RFC in the rfc dir is malformed: one "invalid RFC: <name>: <why>" line per bad RFC.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RFC_DIR = os.path.join(HERE, "rfcs")
SIGNIFICANT_DIR = ".config/aistack"
TEMPLATE = ".config/aistack/rfc-template.md"
STATUSES = ("draft", "review", "approved", "implemented")
COVERING = ("approved", "implemented")


def parse_rfc(path):
    """The frontmatter of an RFC.

    The frontmatter is the lines between the first two '---' lines, split on the first ':'. `touches` becomes a list
    split on commas and stripped; every other key keeps its stripped string value. A file with no frontmatter gives {}.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key:
            fm[key] = value
    if "touches" in fm:
        fm["touches"] = [p.strip() for p in fm["touches"].split(",") if p.strip()]
    return fm


def is_significant(path):
    """True for a .py file directly in .config/aistack/ or a file named planner-prompt.md; False for everything else."""
    p = str(path).replace("\\", "/").strip().rstrip("/")
    while p.startswith("./"):
        p = p[2:]
    name = p.rsplit("/", 1)[-1]
    if name == "planner-prompt.md":
        return True
    return name.endswith(".py") and os.path.dirname(p) == SIGNIFICANT_DIR


def git_changed(base):
    """The changed paths from `git diff --name-only <base>...HEAD` in the git root of this script's directory."""
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=HERE,
        capture_output=True,
        text=True,
    )
    root = top.stdout.strip() if top.returncode == 0 and top.stdout.strip() else HERE
    diff = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if diff.returncode != 0:
        return []
    return [ln.strip() for ln in diff.stdout.splitlines() if ln.strip()]


def load_rfcs(rfc_dir):
    """Every *.md in the rfc dir except README.md, as (name, path), sorted by name. A missing dir is empty."""
    if not os.path.isdir(rfc_dir):
        return []
    return [
        (name, os.path.join(rfc_dir, name))
        for name in sorted(os.listdir(rfc_dir))
        if name.endswith(".md")
        and name != "README.md"
        and os.path.isfile(os.path.join(rfc_dir, name))
    ]


def check_rfcs(rfcs):
    """(invalid, covered): the (name, why) pairs of malformed RFCs and the paths approved/implemented RFCs touch."""
    invalid, covered = [], set()
    for name, path in rfcs:
        fm = parse_rfc(path)
        status = fm.get("status", "")
        if status not in STATUSES:
            invalid.append(
                (name, "missing status" if not status else f"invalid status: {status}")
            )
            continue
        if not fm.get("touches"):
            invalid.append((name, "missing touches"))
            continue
        if status in COVERING:
            covered.update(fm["touches"])
    return invalid, covered


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fail when a significant aidev change has no approved RFC."
    )
    ap.add_argument(
        "--rfc-dir", default=DEFAULT_RFC_DIR, help="directory holding the *.md RFCs"
    )
    ap.add_argument("--base", default="main", help="base ref for the git diff")
    ap.add_argument(
        "--changed",
        nargs="*",
        default=None,
        help="changed paths (default: git diff against --base)",
    )
    args = ap.parse_args(argv)

    changed = git_changed(args.base) if args.changed is None else args.changed

    invalid, covered = check_rfcs(load_rfcs(args.rfc_dir))
    if invalid:
        for name, why in invalid:
            print(f"invalid RFC: {name}: {why}")
        return 2

    uncovered = [p for p in changed if is_significant(p) and p not in covered]
    if not uncovered:
        print("rfc_check: ok")
        return 0
    for p in uncovered:
        print(f"RFC required: {p}")
    print(
        f"Add an approved or implemented RFC listing these paths in touches (start from {TEMPLATE})."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
