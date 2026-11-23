#!/usr/bin/env python3
"""Test the context handoff: a context trip gives the next attempt the diff and the progress note, and the second overflow escalates."""

import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import types

os.environ.pop("AIDEV_GUARD_OVERFLOW_ESCALATE_AFTER", None)
os.environ.pop("AIDEV_GUARD_HANDOFF_DIFF_CHARS", None)

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []
BUILDER = "build-local-tier-2"
REAL = {}


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def trip(t, reason, tmp, diff="diff line one"):
    """guard_trip on a fake run with stubbed tuios, wait_rest, tier_of, reset_pane and git_out; returns t."""
    REAL.update(
        {
            name: getattr(a, name)
            for name in ("tuios", "wait_rest", "tier_of", "reset_pane", "git_out")
            if name not in REAL
        }
    )
    a.tuios = lambda *_args, **_kw: (0, "", "")
    a.wait_rest = lambda *_args, **_kw: True
    a.tier_of = lambda *_args, **_kw: "tier-2"
    a.reset_pane = lambda *_args, **_kw: True
    a.git_out = lambda _wd, *_args: diff
    run = types.SimpleNamespace(
        session="s",
        dir=tmp,
        data={"tasks": {"T1": t}, "work_dir": "/wd"},
        event=lambda *_args, **_kw: None,
        save=lambda: None,
    )
    with contextlib.redirect_stdout(io.StringIO()):
        a.guard_trip(run, BUILDER, "T1", reason)
    for name, value in REAL.items():
        setattr(a, name, value)
    REAL.clear()
    return t


def main():
    g = a.aidev_guard

    diff = "A" * (g.HANDOFF_DIFF_CHARS + 20) + "BBBBB"
    tail = diff[-g.HANDOFF_DIFF_CHARS :]
    note = g.handoff_note(1, "truncated", diff, "")
    check("note names attempt and reason", "ran out of context (truncated)" in note)
    check(
        "note keeps the diff tail and cuts at HANDOFF_DIFF_CHARS",
        tail in note and "A" * (g.HANDOFF_DIFF_CHARS + 1) not in note,
    )
    check("empty progress reads as none", "Progress note:\nnone" in note)
    note = g.handoff_note(2, "context overflow", "diff", "did the first file")
    check("progress text is kept", "Progress note:\ndid the first file" in note)
    check(
        "note tells the builder what to do",
        "Do only the remaining part, in small steps" in note,
    )

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "tasks"))
        with open(os.path.join(tmp, "tasks", "T1-progress.txt"), "w") as fh:
            fh.write("did the first file")

        t = trip({"status": "sent", "attempts": 1, "notes": []}, "context full", tmp)
        check("first context trip leaves tripped unset", not t.get("tripped"))
        check(
            "first context trip appends the handoff note",
            len(t["notes"]) == 1
            and "ran out of context (context full)" in t["notes"][0]
            and "did the first file" in t["notes"][0]
            and "diff line one" in t["notes"][0],
        )
        check("first context trip counts one overflow", t["overflows"] == 1)
        check("the task still fails", t["status"] == "failed")

        t = trip(t, "context full", tmp)
        check("second context trip sets tripped", t.get("tripped") == "context full")
        check("second context trip counts two overflows", t["overflows"] == 2)

        t = trip({"status": "sent", "attempts": 1, "notes": []}, "truncated", tmp)
        check(
            "'truncated' counts as an overflow",
            t["overflows"] == 1 and not t.get("tripped"),
        )

        t = trip({"status": "sent", "attempts": 1, "notes": []}, "loop", tmp)
        check(
            "'loop' sets tripped at once",
            t.get("tripped") == "loop" and t.get("overflows") is None,
        )
        check(
            "'loop' appends the generic note",
            len(t["notes"]) == 1 and "stopped by the guard (loop)" in t["notes"][0],
        )

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "tasks"))
        t = trip(
            {"status": "sent", "attempts": 1, "notes": []}, "context overflow", tmp
        )
        check(
            "a missing progress file reads as none",
            "Progress note:\nnone" in t["notes"][0],
        )

    out = a.task_prompt(
        {"name": "n"},
        {"id": "T1", "title": "t", "description": "d", "acceptanceCriteria": ["c"]},
        ["true"],
        [],
        progress_path="/run/tasks/T1-progress.txt",
    )
    check(
        "task_prompt carries the progress line when progress_path is given",
        "- Keep a short progress note in /run/tasks/T1-progress.txt (done so far, next step), "
        "update it after each file you finish." in out,
    )
    out = a.task_prompt(
        {"name": "n"},
        {"id": "T1", "title": "t", "description": "d", "acceptanceCriteria": ["c"]},
        ["true"],
        [],
    )
    check(
        "task_prompt without progress_path has no progress line",
        "progress note" not in out,
    )

    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
