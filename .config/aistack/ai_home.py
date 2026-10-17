#!/usr/bin/env python3
"""The shared ~/.ai directory of ainfo, aidev and ai (RFC 0003; stdlib only).

Every file the AI tools write lives under AI_HOME (default ~/.ai):
  rfcs/YYYY-MM-DD-slug.md     RFCs any model may write and any tool may start from (format: ~/.ai/README.md)
  handoffs/YYYY-MM-DD-slug/   /aidev-handoff output (prd.json, verify.json)
  ainfo/<project key>/        ainfo state, transcripts and advice
  aidev/<project key>/        aidev plans, runs, reviews and questions
  ai/                         ai's pi agent dir
  cache/<tool>/               model caches, locks and server state
  guard/                      advisor and edit-router state; no model may write here

  ai_home.py --write-rfc FILE [--source S] [--repo R]   save FILE (or - for stdin) as an RFC, print its path
"""

import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
TEMPLATE = os.path.join(os.path.dirname(HERE), "ai", "rfc-template.md")
STATUSES = ("draft", "ready", "in-progress", "done", "dropped")
KEY_ORDER = ("title", "status", "date", "author", "source", "repo", "touches")


def home():
    return os.path.expanduser(os.environ.get("AI_HOME") or os.path.join(os.path.expanduser("~"), ".ai"))


def path(*parts):
    return os.path.join(home(), *parts)


def template():
    try:
        with open(TEMPLATE, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:60].rstrip("-") or "rfc"


def split_frontmatter(text):
    """(dict, body): the keys between the first two '---' lines, split on the first ':', and the rest of the text."""
    lines = text.lstrip("﻿").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines or lines[0].strip() != "---":
        return {}, text
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            fm = {}
            for kv in lines[1:i]:
                k, sep, v = kv.partition(":")
                if sep and k.strip():
                    fm[k.strip()] = v.strip()
            return fm, "\n".join(lines[i + 1 :]).lstrip("\n")
    return {}, text


def write_rfc(text, title="", source="", repo=""):
    """Save an RFC as rfcs/YYYY-MM-DD-slug.md and return its path.

    text may carry its own frontmatter; title, status, date, source and repo are filled in where missing (title from
    the argument, else the first '# ' heading). A name that is taken gets -2, -3, ...: nothing is overwritten.

    Refuses with PermissionError, before creating anything, when rfcs/ resolves outside AI_HOME or into guard/
    in any letter case (a symlinked rfcs/ is followed).
    """
    fm, body = split_frontmatter(text.strip() + "\n")
    if not fm.get("title"):
        m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        fm["title"] = title or (m.group(1).strip() if m else "untitled")
    if fm.get("status") not in STATUSES:
        fm["status"] = "draft"
    today = datetime.date.today().isoformat()
    fm.setdefault("date", today)
    if source:
        fm.setdefault("source", source)
    if repo:
        fm.setdefault("repo", repo)
    keys = [k for k in KEY_ORDER if fm.get(k)] + [k for k in fm if k not in KEY_ORDER and fm[k]]
    out = "---\n" + "".join(f"{k}: {fm[k]}\n" for k in keys) + "---\n\n" + body.rstrip() + "\n"
    d = path("rfcs")
    real_home = os.path.realpath(home())
    real_d = os.path.realpath(d)
    if real_d == real_home or not (real_d + "/").startswith(real_home + "/"):
        raise PermissionError(f"rfcs dir {real_d} is outside {real_home}")
    if (real_d + "/").lower().startswith((os.path.join(real_home, "guard") + "/").lower()):
        raise PermissionError(f"rfcs dir {real_d} is inside guard/")
    os.makedirs(d, exist_ok=True)
    base = f"{today}-{slug(fm['title'])}"
    for n in range(1, 1000):
        p = os.path.join(d, base + (f"-{n}" if n > 1 else "") + ".md")
        try:
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(out)
        return p
    raise OSError(f"no free RFC name for {base} in {d}")


def main(argv):
    if len(argv) < 2 or argv[0] != "--write-rfc":
        print(__doc__.strip(), file=sys.stderr)
        return 2
    opts = dict(zip(argv[2::2], argv[3::2]))
    text = sys.stdin.read() if argv[1] == "-" else open(argv[1], encoding="utf-8").read()
    try:
        print(write_rfc(text, source=opts.get("--source", ""), repo=opts.get("--repo", "")))
    except PermissionError as e:
        print(f"ai_home: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
