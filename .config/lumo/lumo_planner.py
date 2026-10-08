#!/usr/bin/env python3
"""Planning loop: Lumo thinks, a local llama.cpp model fetches files.

Lumo (via lumo-tamer, tools disabled) is told to end replies with `NEED:` lines
when it wants more context. Each NEED is resolved from a project root:
exact paths are read directly, anything else goes to a small local model that
uses read-only tools (list/glob/grep/read). Results go back to Lumo as the next
user message. Stdlib only.

Used as a library by aidev (.config/aistack/ralph_mcp.py imports it and calls run_loop
with the current project as root) and as a one-shot command (see --help). It used to
run as a daemon too, a proxy on port 8765 tied to one repository; that is gone.
"""
import argparse
import fnmatch
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

LUMO_BASE_URL = os.environ.get("LUMO_BASE_URL", "http://localhost:3000/v1")
LUMO_MODEL = os.environ.get("LUMO_MODEL", "lumo")
LUMO_API_KEY = os.environ.get("LUMO_API_KEY", "")
# Bearer token clients of this proxy must send. Required when listening beyond loopback.
LOCAL_BASE_URL = os.environ.get("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1")
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "qwen/qwen3.5-9b")

# keyword (default, no model needed) or llm (local model with read-only tools)
RESOLVER = os.environ.get("RESOLVER", "keyword")

MAX_FILE_BYTES = 200_000
MAX_TOOL_CHARS = 6_000
MAX_RESULT_CHARS = 12_000
MAX_RESOLVER_STEPS = 6

# Hard privacy gate. Applied to every path before anything is read or listed.
DENY_DIRS = {".git", "node_modules", ".terraform", "secrets", ".ssh", ".gnupg"}
# Noise, not secrets: left out of keyword search only (explicit paths still readable).
SKIP_DIRS = {".mypy_cache", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv",
             ".worktrees", ".token-optimizer", ".idea", ".vscode"}
DENY_GLOBS = [
    ".env*", "*.tfvars", "*.tfstate*", "*.pem", "*.key", "*.p12", "*.pfx",
    "id_rsa*", "id_ed25519*", "*kubeconfig*", "*.age", "*.sops.*", "*secret*",
    "*credential*", "*.kdbx", ".doppler*", ".netrc", "*.token",
]

SYSTEM_PROMPT = """You are a planning assistant for an infrastructure repository.
You cannot read files yourself. A helper can fetch repository context for you.
To request context, end your reply with one line per request, using one of these forms:
NEED: <repo-relative path>
NEED: ls <directory>
NEED: find <glob pattern, e.g. *matrix*.yaml>
NEED: grep <regex> [in <directory>]
NEED: <a few distinctive keywords, e.g. argocd matrix hetzner application>
Keyword requests rank files by how many of the words match the path and content, so
use specific words (names, kinds, tools) and skip filler. Use exact paths when you know them.
Request only what you need. When you have enough context, give the final plan and write no NEED lines."""

RESOLVER_PROMPT = """You find files in a repository for another assistant. Use the tools to locate
what the request describes, then reply with the relevant file paths and short
excerpts of the relevant lines only. Be brief. Do not explain or plan.
Never guess paths. Start with list on "." and drill into the matching directories,
use grep with a keyword from the request to find content, and read the best match.
Keep using tools until you find it or run out of steps; do not answer "not found"
after only a few failed guesses."""

NEED_RE = re.compile(r"^\s*(?:[-*]\s*)?NEED\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def post_chat(base_url, payload, api_key=""):
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)["choices"][0]["message"]


class Sandbox:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def denied(self, rel):
        parts = Path(rel).parts
        if any(p in DENY_DIRS for p in parts):
            return True
        return any(fnmatch.fnmatch(p.lower(), g) for p in parts for g in DENY_GLOBS)

    def resolve(self, rel):
        """Return (absolute path, error). Rejects escapes, symlink escapes, denied paths."""
        p = (self.root / rel).resolve()
        try:
            r = p.relative_to(self.root)
        except ValueError:
            return None, "path outside root"
        if self.denied(r):
            return None, "path denied by policy"
        return p, None

    def walk(self, base):
        for dirpath, dirnames, filenames in os.walk(base):
            rel_dir = Path(dirpath).relative_to(self.root)
            dirnames[:] = [d for d in dirnames if not self.denied(rel_dir / d)]
            for f in filenames:
                rel = rel_dir / f
                if not self.denied(rel):
                    yield rel

    def read(self, rel, start=1, end=None):
        p, err = self.resolve(rel)
        if err:
            return f"error: {err}"
        if not p.is_file():
            return "error: not a file"
        if p.stat().st_size > MAX_FILE_BYTES:
            return f"error: file larger than {MAX_FILE_BYTES} bytes, use grep or a line range"
        try:
            lines = p.read_text(errors="strict").splitlines()
        except (UnicodeDecodeError, OSError):
            return "error: unreadable or binary file"
        end = end or len(lines)
        body = "\n".join(f"{i}: {l}" for i, l in enumerate(lines[start - 1:end], start))
        return body[:MAX_TOOL_CHARS] + ("\n[truncated]" if len(body) > MAX_TOOL_CHARS else "")

    def list(self, rel="."):
        p, err = self.resolve(rel)
        if err:
            return f"error: {err}"
        if not p.is_dir():
            return "error: not a directory"
        out = []
        for c in sorted(p.iterdir()):
            r = c.relative_to(self.root)
            if not self.denied(r):
                out.append(str(r) + ("/" if c.is_dir() else ""))
        return "\n".join(out)[:MAX_TOOL_CHARS]

    def glob(self, pattern):
        out = [str(r) for r in self.walk(self.root) if fnmatch.fnmatch(str(r), pattern)]
        return "\n".join(sorted(out)[:200]) or "no matches"

    def grep(self, pattern, path="."):
        p, err = self.resolve(path)
        if err:
            return f"error: {err}"
        try:
            rx = re.compile(pattern)
        except re.error as e:
            return f"error: bad regex: {e}"
        base = p if p.is_dir() else p.parent
        files = self.walk(base) if p.is_dir() else [p.relative_to(self.root)]
        hits = []
        for rel in files:
            fp = self.root / rel
            try:
                if fp.stat().st_size > MAX_FILE_BYTES:
                    continue
                for i, line in enumerate(fp.read_text(errors="strict").splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{rel}:{i}: {line.strip()[:200]}")
                        if len(hits) >= 80:
                            return "\n".join(hits) + "\n[truncated]"
            except (UnicodeDecodeError, OSError):
                continue
        return "\n".join(hits) or "no matches"


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "what", "which", "where",
    "how", "its", "are", "was", "can", "all", "any", "not", "but", "you", "your", "our",
    "use", "using", "file", "files", "path", "give", "tell", "find", "show", "need", "then",
    "plain", "description", "definition", "manifest", "config", "configuration", "repo",
    "repository", "about", "has", "have", "there", "their", "them", "when", "also",
}
TERM_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*")


def query_terms(text):
    """Distinctive lowercase keywords from a free-text request (max 12)."""
    terms = []
    for w in TERM_RE.findall(text.lower()):
        w = w.strip("._-")
        if len(w) < 3 or w in STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        if w not in terms:
            terms.append(w)
    return terms[:12]


class KeywordIndex:
    """Lowercased text of every allowed file, rebuilt at most once per TTL seconds."""
    TTL = 60

    def __init__(self, sb):
        self.sb = sb
        self.files = {}
        self.built = 0.0

    def refresh(self):
        if time.time() - self.built < self.TTL:
            return
        seen = {}
        for rel in self.sb.walk(self.sb.root):
            if any(p in SKIP_DIRS for p in rel.parts):
                continue
            fp = self.sb.root / rel
            try:
                mtime = fp.stat().st_mtime
                size = fp.stat().st_size
            except OSError:
                continue
            old = self.files.get(rel)
            if old and old[0] == mtime:
                seen[rel] = old
                continue
            text = None
            if size <= MAX_FILE_BYTES:
                try:
                    text = fp.read_text(errors="strict").lower()
                except (UnicodeDecodeError, OSError):
                    pass
            seen[rel] = (mtime, text)
        self.files, self.built = seen, time.time()

    def search(self, request, limit=5):
        """Rank files by IDF-weighted keyword matches in path (x3) and content."""
        terms = query_terms(request)
        if not terms:
            return terms, []
        self.refresh()
        hits, df = {}, Counter()
        for rel, (_, low) in self.files.items():
            p = str(rel).lower()
            pt = {t for t in terms if t in p}
            ct = {t for t in terms if low and t in low}
            if pt or ct:
                hits[rel] = (pt, ct)
                df.update(pt | ct)
        n = max(len(self.files), 1)
        weight = {t: math.log(1 + n / df[t]) if df[t] else 0.0 for t in terms}
        def score(rel, pt, ct):
            s = sum(3 * weight[t] for t in pt) + sum(weight[t] for t in ct - pt)
            # a term that IS the file name or a directory name is a much stronger signal
            stem = query_terms(rel.stem.replace("_", " "))
            s += sum(4 * weight[t] for t in pt if t in stem or t == rel.stem.lower())
            s += sum(2 * weight[t] for t in pt if t in {p.lower() for p in rel.parts[:-1]})
            return s

        scored = [(score(rel, pt, ct), rel, pt | ct) for rel, (pt, ct) in hits.items()]
        scored.sort(key=lambda x: (-x[0], len(str(x[1]))))
        return terms, scored[:limit]

    def excerpts(self, rel, matched, max_lines=3):
        try:
            lines = (self.sb.root / rel).read_text(errors="strict").splitlines()
        except (UnicodeDecodeError, OSError):
            return []
        ranked = []
        for i, line in enumerate(lines, 1):
            low = line.lower()
            k = sum(1 for t in matched if t in low)
            if k:
                ranked.append((-k, i, line.strip()[:160]))
        ranked.sort()
        return [f"  {i}: {txt}" for _, i, txt in sorted(ranked[:max_lines], key=lambda x: x[1])]


CMD_RE = re.compile(r"^(ls|find|grep)\s*:?\s+(.+)$", re.IGNORECASE)


def keyword_resolve(sb, index, request):
    terms, results = index.search(request)
    if not results:
        top = sb.list(".")
        return (f"[{request}]\nno files matched keywords {terms or '(none usable)'}."
                f" Top-level entries:\n{top}")
    out = [f"[{request}] keywords: {', '.join(terms)}"]
    for score, rel, matched in results:
        out.append(f"{rel}  (score {score:.1f}; matched: {', '.join(sorted(matched))})")
        out.extend(index.excerpts(rel, matched))
    return "\n".join(out)


TOOLS = [
    {"type": "function", "function": {
        "name": "list", "description": "List a directory (repo-relative).",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "glob", "description": "Find files by glob pattern, e.g. k3s-apps/*/kustomization.yaml.",
        "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "grep", "description": "Regex search file contents under a path.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "read", "description": "Read a file with line numbers, optional line range.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}},
            "required": ["path"]}}},
]


def run_tool(sb, name, args):
    try:
        if name == "list":
            return sb.list(args.get("path", "."))
        if name == "glob":
            return sb.glob(args["pattern"])
        if name == "grep":
            return sb.grep(args["pattern"], args.get("path", "."))
        if name == "read":
            return sb.read(args["path"], int(args.get("start") or 1), args.get("end"))
    except (KeyError, TypeError, ValueError) as e:
        return f"error: bad arguments: {e}"
    return f"error: unknown tool {name}"


def resolve_need(sb, request):
    """Exact path -> read. `ls`/`find`/`grep` -> sandbox tools. Otherwise keyword search
    (default) or, with RESOLVER=llm, a local model driving read-only tools."""
    cand = request.strip().strip("`'\"")
    if " " not in cand:
        p, err = sb.resolve(cand)
        if err:
            return f"[{cand}] {err}"
        if p.is_file():
            return f"[{cand}]\n{sb.read(cand)}"
        if p.is_dir():
            return f"[{cand}/]\n{sb.list(cand)}"

    m = CMD_RE.match(request.strip())
    if m:
        cmd, arg = m.group(1).lower(), m.group(2).strip().strip("`'\"")
        if cmd == "ls":
            return f"[ls {arg}]\n{sb.list(arg)}"
        if cmd == "find":
            return f"[find {arg}]\n{sb.glob(arg)}"
        pattern, _, where = arg.rpartition(" in ")
        if not pattern:
            pattern, where = arg, "."
        return f"[grep {pattern} in {where.strip()}]\n{sb.grep(pattern.strip(), where.strip())}"

    if RESOLVER == "llm":
        return llm_resolve(sb, request)
    if not hasattr(sb, "index"):
        sb.index = KeywordIndex(sb)
    return keyword_resolve(sb, sb.index, request)


def llm_resolve(sb, request):
    messages = [
        {"role": "system", "content": RESOLVER_PROMPT},
        {"role": "user", "content": request},
    ]
    for _ in range(MAX_RESOLVER_STEPS):
        msg = post_chat(LOCAL_BASE_URL, {
            "model": LOCAL_MODEL, "messages": messages, "tools": TOOLS, "temperature": 0,
            # Qwen3.5 on llama-server ignores /no_think and reasoning_effort; chat_template_kwargs.enable_thinking works
            "chat_template_kwargs": {"enable_thinking": False},
        })
        calls = msg.get("tool_calls")
        if not calls:
            return f"[{request}]\n{(msg.get('content') or '').strip()}"
        messages.append(msg)
        for c in calls:
            fn = c["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            log(f"    tool {fn['name']} {args}")
            messages.append({
                "role": "tool", "tool_call_id": c["id"],
                "content": run_tool(sb, fn["name"], args),
            })
    return f"[{request}]\nresolver gave no answer within {MAX_RESOLVER_STEPS} steps"


def run_loop(sb, messages, max_rounds, cache=None, on_progress=None):
    """Drive Lumo until it stops emitting NEED lines. Returns (text, complete)."""
    cache = {} if cache is None else cache
    note = on_progress or (lambda _m: None)
    text = ""
    for rnd in range(1, max_rounds + 1):
        log(f"round {rnd}: asking Lumo")
        note(f"round {rnd}: asking Lumo")
        reply = post_chat(LUMO_BASE_URL, {"model": LUMO_MODEL, "messages": messages}, LUMO_API_KEY)
        text = reply.get("content") or ""
        needs = NEED_RE.findall(text)
        if not needs:
            return text, True
        if rnd == max_rounds:
            log("round cap reached, returning last reply")
            return text, False
        messages.append({"role": "assistant", "content": text})
        results = []
        for n in needs:
            log(f"  NEED: {n}")
            note(f"fetching: {n}")
            if n not in cache:
                cache[n] = resolve_need(sb, n)
            results.append(cache[n])
        body = "\n\n".join(results)[:MAX_RESULT_CHARS]
        messages.append({"role": "user", "content": "Requested context:\n\n" + body})
    return text, False


def flatten(content):
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


SYSTEM_PROMPT_NOFETCH = """You are a planning assistant for a software project.
Everything you need is in the message. You cannot read files and nobody can fetch more context,
so do not ask for files: state assumptions and open questions in your answer instead."""


def upstream_messages(client_messages, fetch=True):
    """Client history -> Lumo history. Tool messages and tool_calls are dropped.
    fetch=False (header X-Lumo-No-Fetch: 1) swaps the NEED instructions for a self-contained prompt."""
    system = SYSTEM_PROMPT if fetch else SYSTEM_PROMPT_NOFETCH
    out = []
    for m in client_messages:
        role, text = m.get("role"), flatten(m.get("content"))
        if role in ("system", "developer"):
            system += "\n\n" + text
        elif role in ("user", "assistant") and text:
            out.append({"role": role, "content": text})
    return [{"role": "system", "content": system}] + out


def cli(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("task", help="what to plan")
    ap.add_argument("-f", "--file", action="append", default=[], help="initial repo-relative file (repeatable)")
    ap.add_argument("-r", "--root", default=os.getcwd(), help="repo root (default: cwd)")
    ap.add_argument("--max-rounds", type=int, default=5)
    a = ap.parse_args(argv)

    sb = Sandbox(a.root)
    intro = a.task
    for f in a.file:
        intro += f"\n\n[{f}]\n{sb.read(f)}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": intro}]
    text, complete = run_loop(sb, messages, a.max_rounds)
    print(text)
    return 0 if complete else 1


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
