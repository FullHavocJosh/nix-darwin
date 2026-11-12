"""Rewrite the detailed PR task list into a short description for a human reviewer."""

import re

SYSTEM = (
    "You write a short pull request description for a human reviewer. "
    "Write exactly this layout: a '## Summary' heading followed by a paragraph of one to two sentences, "
    "then a '## Changes' heading followed by at most 5 bullets, each starting with '- ', "
    "saying what changed and why. "
    "Do not mention task ids such as T1 or T2. Do not list verify commands. "
    "Do not use emojis or em-dashes. Do not mention AI or tools. "
    "Do not add any other headings. Reply with the description only."
)
REF_RE = re.compile(r"(?<![\w&/#])#(\d+)(?!\w)")
CODE_RE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)


def build_input(prd, diff_stat, body=""):
    """Plan title, description, stories and the diff stat; the current PR body stands in for an empty plan."""
    parts = []
    if prd:
        parts.append(f"Title: {prd.get('title', '')}")
        parts.append(f"Description: {prd.get('description', '')}")
        for story in prd.get("userStories") or []:
            parts.append(f"Story: {story.get('title', '')}")
            for criterion in story.get("acceptanceCriteria") or []:
                parts.append(f"- {criterion}")
    else:
        parts.append(f"Current pull request body:\n{body}")
    parts.append(f"Diff stat:\n{diff_stat}")
    return "\n".join(parts)


def _wrap_refs(text):
    pieces = CODE_RE.split(text)
    return "".join(p if i % 2 else REF_RE.sub(r"`#\1`", p) for i, p in enumerate(pieces))


def clean(reply, fallback):
    text = (reply or "").strip()
    if not text or "## Summary" not in text:
        return fallback
    return _wrap_refs(text)


def describe(prd, diff_stat, ask, fallback, body=""):
    try:
        reply = ask(build_input(prd, diff_stat, body), SYSTEM)
    except RuntimeError:
        return fallback
    return clean(reply, fallback)
