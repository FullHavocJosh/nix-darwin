"""Guard constants and TaskGuard trip logic.

Stdlib only. Constants are overridable via env vars AIDEV_GUARD_<NAME>.
"""

import json
import os
import re
import time


def _env_int(name, default):
    """Read an int from AIDEV_GUARD_<NAME> or return default."""
    s = os.environ.get(f"AIDEV_GUARD_{name}")
    if s is None:
        return default
    try:
        return int(s.strip())
    except ValueError:
        return default


# Constants at module top, each overridable by an env var AIDEV_GUARD_<NAME>
IDLE_REAP_S = _env_int("IDLE_REAP_S", 120)
PLAN_DONE_REAP_S = _env_int("PLAN_DONE_REAP_S", 30)
TASK_WALL_S = _env_int("TASK_WALL_S", 900)
TASK_TURNS = _env_int("TASK_TURNS", 40)
LOOP_REPEAT = _env_int("LOOP_REPEAT", 3)
HASH_REPEAT = _env_int("HASH_REPEAT", 2)
NO_PROGRESS_S = _env_int("NO_PROGRESS_S", 300)


class TaskGuard:
    """Trip logic for monitoring builder activity."""

    def __init__(self, clock=None, calls_known=True):
        self.start = clock() if clock else time.time()
        self.last_progress = self.start
        self.turns = 0
        self.recent = []
        self.diff = None
        self.done_at = None
        self.calls_known = calls_known
        self.clock = clock

    def _now(self):
        """Get current time using the provided clock or time.time()."""
        return self.clock() if self.clock else time.time()

    def observe(self, calls, diff_hash=None):
        """Observe new tool calls and a diff_hash.

        Args:
            calls: list of new tool-call dicts since the last observe, each
                {'tool': str, 'args': str, 'out': str}
            diff_hash: diff hash that also resets progress tracking

        Returns:
            Trip reason string or None if no trip occurred.
        """
        if calls is None:
            calls = []

        # Check 'turn after done' first (beats all others)
        if self.done_at is not None and calls:
            return "turn after done"

        # Update with new calls
        for call in calls:
            self.turns += 1
            self.last_progress = self._now()
            self.recent.append(call)
            # Keep recent at most 10
            if len(self.recent) > 10:
                self.recent = self.recent[-10:]

        # Handle diff_hash - if different from self.diff, reset progress
        if diff_hash is not None and diff_hash != self.diff:
            self.last_progress = self._now()
            self.diff = diff_hash

        # Check trip conditions
        # wall clock
        if self._now() - self.start >= TASK_WALL_S:
            return "wall clock"

        # turns (only if calls_known)
        if self.calls_known and self.turns >= TASK_TURNS:
            return "turns"

        # loop - last LOOP_REPEAT calls have the same (tool, args)
        if len(self.recent) >= LOOP_REPEAT:
            first_call = self.recent[-LOOP_REPEAT]
            if all(
                call["tool"] == first_call["tool"]
                and call["args"] == first_call["args"]
                for call in self.recent[-LOOP_REPEAT:]
            ):
                return "loop"

        # same output - a call has non-empty out equal to the previous call's out
        if len(self.recent) >= 2:
            prev_call = self.recent[-2]
            curr_call = self.recent[-1]
            prev_out = prev_call.get("out", "")
            curr_out = curr_call.get("out", "")
            if curr_out and curr_out == prev_out:
                return "same output"

        # no progress
        if self._now() - self.last_progress >= NO_PROGRESS_S:
            return "no progress"

        return None

    def mark_done(self):
        """Mark the task as done."""
        self.done_at = self._now()

    def to_dict(self):
        """Return a JSON-safe dict of all attributes."""
        return {
            "start": self.start,
            "last_progress": self.last_progress,
            "turns": self.turns,
            "recent": self.recent,
            "diff": self.diff,
            "done_at": self.done_at,
            "calls_known": self.calls_known,
        }

    @classmethod
    def from_dict(cls, d, clock=None, calls_known=True):
        """Rebuild TaskGuard from a dict."""
        instance = cls(clock=clock, calls_known=calls_known)
        instance.start = d.get("start")
        instance.last_progress = d.get("last_progress")
        instance.turns = d.get("turns", 0)
        instance.recent = d.get("recent", [])
        instance.diff = d.get("diff")
        instance.done_at = d.get("done_at")
        instance.calls_known = calls_known
        return instance


# Idle reaper decision logic


def reap_due(state, since, now, task_queued, plan_done) -> bool:
    """Check if a pane should be reaped (closed) due to being idle.

    Args:
        state: the tuios agent state string of a builder pane
        since: the time (seconds, same unit as now) the pane first showed a resting state
        now: the current time
        task_queued: a bool (a task with status 'sent' or 'pending' exists for this builder)
        plan_done: a bool

    Returns:
        True if the pane should be reaped, False otherwise.

    Rules:
        - Return False when state is not in ('idle', 'done', 'none')
        - Return False when since is None
        - Return False when task_queued is True
        - Otherwise limit = PLAN_DONE_REAP_S when plan_done else IDLE_REAP_S
        - Return True when now - since >= limit
    """
    if state not in ("idle", "done", "none"):
        return False
    if since is None:
        return False
    if task_queued:
        return False
    limit = PLAN_DONE_REAP_S if plan_done else IDLE_REAP_S
    return now - since >= limit


class RestTracker:
    """Track resting states for builder panes.

    Keeps the first since seen for a resting state ('idle','done','none')
    and resets to clock() when a new resting state is seen.
    Any other state deletes the entry.
    """

    def __init__(self, clock=time.time):
        self._clock = clock
        self._resting = {}

    def update(self, name, state) -> float | None:
        """Update or add a resting state for a pane.

        Args:
            name: the pane name
            state: the tuios agent state string

        Returns:
            The since time for this pane, or None if the state is not resting.
        """
        if state in ("idle", "done", "none"):
            if name not in self._resting:
                self._resting[name] = self._clock()
            else:
                self._resting[name] = self._clock()
            return self._resting[name]
        else:
            self._resting.pop(name, None)
            return None

    def forget(self, name):
        """Forget a pane's tracking."""
        if name in self._resting:
            del self._resting[name]


CONTEXT_FILL_PCT = _env_int("CONTEXT_FILL_PCT", 80)


def context_trip(text) -> str | None:
    """Trip logic for pane capture based on footer fill or truncation.

    Args:
        text: the text of the pane capture

    Returns:
        'context full' when footer percentage >= CONTEXT_FILL_PCT,
        'truncated' when text contains 'Response was truncated' (case-insensitive),
        None otherwise.

    Rules:
        - Truncation wins over fill.
        - Only the last footer match counts (find all matches, use the last one).
    """
    # Check truncation first (takes precedence)
    if "response was truncated" in text.lower():
        return "truncated"

    # Find the last footer match
    last_match = None
    for m in re.finditer(r"(\d+(?:\.\d+)?)%/\d+k", text):
        last_match = m

    if last_match is None:
        return None

    pct_str = last_match.group(1)
    pct = float(pct_str)

    if pct >= CONTEXT_FILL_PCT:
        return "context full"

    return None


def read_tool_log(path, offset=0) -> tuple[list[dict], int]:
    """Read tool calls from a binary log file, returning only complete lines.

    Args:
        path: path to the log file (binary mode)
        offset: starting offset in bytes

    Returns:
        Tuple of (list of {'tool': str, 'args': str, 'out': str} dicts, new_offset).
        A missing file returns ([], offset).
        Garbage lines are skipped.
    """
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read()
    except FileNotFoundError:
        return [], offset
    except Exception:
        # Log the exception and return empty list with original offset
        import sys

        print(f"Error reading log file: {sys.exc_info()[0]}", file=sys.stderr)
        return [], offset

    # Split on newlines, keep only complete lines (stop at last b'\n')
    if not data:
        return [], offset

    # Find the last newline
    last_newline = data.rfind(b"\n")
    if last_newline == -1:
        # No newlines at all, treat as partial line - no calls, offset unchanged
        return [], offset

    # Complete lines end at last_newline
    complete_lines = data[: last_newline + 1].split(b"\n")
    new_offset = offset + len(data[: last_newline + 1])

    calls = []
    for line_bytes in complete_lines:
        if not line_bytes:
            continue
        try:
            line = line_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Garbage line, skip
            continue
        try:
            obj = json.loads(line)
            calls.append(
                {
                    "tool": obj.get("tool", ""),
                    "args": obj.get("args", ""),
                    "out": obj.get("out", ""),
                }
            )
        except Exception:  # noqa: S112
            # Garbage line, skip it and continue to next line
            continue

    return calls, new_offset


# per-tier pi window; keep equal to aidev_tiers DEFAULTS ctx
CONTEXT_WINDOW = {"tier-0": 32768, "tier-1": 8192, "tier-2": 65536, "tier-3": 65536, "tier-4": 65536}


def preflight(tier_id, prompt_tokens, output_cap) -> tuple[bool, str]:
    """Refuse a task that cannot fit the tier's window.

    Args:
        tier_id: the builder tier id
        prompt_tokens: the estimated prompt tokens of the task
        output_cap: the tier's max output tokens

    Returns:
        (ok, reason): ok when prompt_tokens + output_cap fit the tier's window;
        a tier not in CONTEXT_WINDOW (tier-5 and tier-6) is always ok; the
        reason names the split when it does not fit, else ''.
    """
    window = CONTEXT_WINDOW.get(tier_id)
    if window is None:
        return True, ""
    if prompt_tokens + output_cap <= window:
        return True, ""
    return False, (
        f"split: about {prompt_tokens} prompt + {output_cap} output tokens "
        f"exceed the {window} window of {tier_id}"
    )


OVERFLOW_ESCALATE_AFTER = _env_int("OVERFLOW_ESCALATE_AFTER", 2)
HANDOFF_DIFF_CHARS = _env_int("HANDOFF_DIFF_CHARS", 3000)
CONTEXT_REASONS = ("context full", "truncated", "context overflow")


def handoff_note(attempt, reason, diff, progress) -> str:
    """The note that hands the next attempt the work of a builder that ran out of context.

    Args:
        attempt: the attempt number of the try that ran out
        reason: the trip reason, one of CONTEXT_REASONS
        diff: the worktree diff so far
        progress: the builder's progress note text, '' when there is none

    Returns:
        The note, cut to the last HANDOFF_DIFF_CHARS chars of the diff and
        with 'none' in place of an empty progress note.
    """
    return (
        f"- Attempt {attempt}: the builder ran out of context ({reason}). Its work so far is in the worktree. "
        f"Diff so far (cut):\n{diff[-HANDOFF_DIFF_CHARS:]}\nProgress note:\n{progress or 'none'}\n"
        "Do only the remaining part, in small steps, read only the line ranges you need, and keep your progress "
        "in the note file named in the task."
    )


if __name__ == "__main__":
    print("aidev_guard module loaded")
    print(f"IDLE_REAP_S: {IDLE_REAP_S}")
    print(f"PLAN_DONE_REAP_S: {PLAN_DONE_REAP_S}")
    print(f"CONTEXT_FILL_PCT: {CONTEXT_FILL_PCT}")
