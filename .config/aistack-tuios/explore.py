"""IO primitives for the plan pane's explore helper: the 9B on :8080 reads code for the plan pane."""

import json
import os
import re
import subprocess
import urllib.request

SYSTEM = (
    "You read source code for a planner. Answer only from the text given. "
    "Give file:line for every claim. At most 1500 characters. No preamble."
)
STOP = {"where", "what", "does", "this", "that", "with", "from", "which", "how"}
BASE = os.environ.get("AIDEV_TUIOS_9B_URL", "http://127.0.0.1:8080")
MAX_9B_CHARS = 40000


def ctx_tokens():
    try:
        with urllib.request.urlopen(BASE + "/props", timeout=3) as r:
            return int(json.load(r)["default_generation_settings"]["n_ctx"])
    except Exception:
        return 0


def ask(prompt, system="", max_tokens=700):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": "qwen/qwen3.5-9b",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        req = urllib.request.Request(
            BASE + "/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(str(e))
    if not out:
        raise RuntimeError("empty reply")
    return out


def read_files(root, files, budget_chars):
    """Return (numbered text of the files, list of 'path: reason' for skipped ones)."""
    root_real = os.path.realpath(root)
    parts = []
    skipped = []
    used = 0
    for rel in files:
        m = re.match(r"^(.*):(\d+)-(\d+)$", rel)
        name, start, end = (m.group(1), int(m.group(2)), int(m.group(3))) if m else (rel, 1, None)
        if m and start > end:
            skipped.append(f"{rel}: bad range")
            continue
        path = os.path.realpath(os.path.join(root_real, name))
        if path != root_real and not path.startswith(root_real + os.sep):
            skipped.append(f"{rel}: outside root")
            continue
        if not os.path.isfile(path):
            skipped.append(f"{rel}: missing")
            continue
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError:
            skipped.append(f"{rel}: missing")
            continue
        if b"\0" in raw[:2000]:
            skipped.append(f"{rel}: binary")
            continue
        lines = raw.decode("utf-8", "replace").splitlines()
        if m:
            if start > len(lines):
                skipped.append(f"{rel}: range past end")
                continue
            end = min(end, len(lines))
        else:
            start, end = 1, len(lines)
        numbered = [f"{i}: {lines[i-1]}" for i in range(start, end + 1)]
        text = f"=== {name} ===\n" + "\n".join(numbered)
        if used + len(text) > budget_chars:
            skipped.append(f"{rel}: over budget")
            break
        parts.append(text)
        used += len(text)
    return "\n".join(parts), skipped


def grep_context(root, question, cap_lines=120):
    words = []
    for w in re.findall(r"[a-z0-9_]+", question.lower()):
        if len(w) >= 4 and w not in STOP and w not in words:
            words.append(w)
        if len(words) == 5:
            break
    hits = []
    for w in words:
        try:
            r = subprocess.run(
                ["git", "-C", root, "grep", "-n", "-i", "-I", "-m", "3", "-F", "-e", w],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        hits += [line[:200] for line in r.stdout.splitlines()]
    return "\n".join(hits[:cap_lines])


def explore(question, files, root, fallback=None, max_chars=1500):
    n = ctx_tokens()
    budget = min(max(0, n - 4200) * 3, MAX_9B_CHARS)
    if files:
        text, skipped = read_files(root, files, budget)
    else:
        text, skipped = grep_context(root, question), []
    prompt = question + "\n\n" + text
    if skipped:
        prompt += "\n\nSkipped: " + "; ".join(skipped)

    def fall():
        if callable(fallback):
            return fallback(prompt)[:max_chars]
        raise RuntimeError("9B unavailable or input too big: name fewer files or file:START-END line ranges")

    if n == 0 or any(s.endswith("over budget") for s in skipped) or not text.strip():
        return fall()
    try:
        answer = ask(prompt, SYSTEM)
    except RuntimeError:
        return fall()
    return answer[:max_chars]
