#!/usr/bin/env python3
"""Idempotent source patch for the claude-tui Homebrew formula (slima4/claude-tui).

Applied by nix-darwin's activation script on every run, since brew upgrades
the formula in place and wipes local edits each time. Each edit is
anchor-checked against pristine upstream text and skipped with a warning
(no crash) if upstream changed it. Silent when already applied.

What it changes, compact statusline only (`claudetui statusline --compact`):

  ▏▯▯▯▯┆▕ C  0% ⚡0/1.0M ⋮ ▏▮▮▮▋▯▯▕ 5-hour 41% resets in 1h02m

1. formatting.py: adds format_usage_constraint(), one usage bar for whichever
   rate_limits window (five_hour, seven_day) is closest to its cap, labeled
   with the window name. Suffix is a linear "~Xh to limit" projection when
   usage is on track to hit the cap before reset, else "resets in <time>".
2. render.py: build_compact_line() drops the model name and shows that one
   widget instead of separate S/W bars. Full (non-compact) mode is untouched.

Earlier versions of this script also patched fetch_usage() caching (only used
by `claudetui monitor`), a monthly cost/token estimate (never displayed: no
budget configured, and it rescanned every transcript on each refresh), a
/usage-sync command, and the model pricing table. The activation wrapper in
packages-tui.nix reinstalls the formula once to clear those.
"""

import os
import sys

FORMATTING_MARKER = "# nix-darwin: combined-usage-widget patch"

OLD_DATETIME_IMPORT = "from datetime import datetime, timezone"
NEW_DATETIME_IMPORT = "from datetime import datetime, timedelta, timezone"

OLD_FORMATTING_TAIL = '''def format_usage_weekly(usage_data, length=20):
    """Format weekly (7-day) usage for display."""
    return _format_usage_bar(usage_data, "seven_day", "W", length)'''

NEW_FORMATTING_TAIL = OLD_FORMATTING_TAIL + '''


''' + FORMATTING_MARKER + '''
# Keys are what Claude Code's stdin rate_limits object carries (see
# code.claude.com/docs/en/statusline); window lengths drive the projection.
_CONSTRAINT_LABELS = {"five_hour": "5-hour", "seven_day": "7-day"}
_CONSTRAINT_WINDOW_SECONDS = {"five_hour": 5 * 3600, "seven_day": 7 * 86400}

# Right after a reset, elapsed time is tiny and any usage projects a false
# "about to hit the cap" alarm; wait this long before trusting the rate.
_MIN_ELAPSED_FOR_PROJECTION_SECONDS = 300


def _most_constraining_window(usage_data):
    best_key, best, best_pct = None, None, -1
    for key in _CONSTRAINT_LABELS:
        window = usage_data.get(key)
        if not isinstance(window, dict):
            continue
        pct = window.get("utilization")
        if isinstance(pct, (int, float)) and pct > best_pct:
            best_key, best, best_pct = key, window, pct
    return best_key, best


def _parse_iso(reset_iso):
    if not isinstance(reset_iso, str) or not reset_iso:
        return None
    try:
        return datetime.fromisoformat(reset_iso.replace("Z", UTC_OFFSET))
    except ValueError:
        return None


def _format_hm(seconds):
    seconds = max(0, int(seconds))
    h, m = seconds // 3600, (seconds % 3600) // 60
    return f"{h}h{m:02d}m" if h > 0 else f"{m}m"


def _project_time_to_cap(key, pct, reset_dt):
    """Seconds until pct hits 100 at the current average rate, or None when
    it would reset first or there is not enough data for a stable rate."""
    duration = _CONSTRAINT_WINDOW_SECONDS.get(key)
    if duration is None or reset_dt is None or pct <= 0:
        return None
    now = datetime.now(timezone.utc)
    elapsed = (now - (reset_dt - timedelta(seconds=duration))).total_seconds()
    if elapsed < _MIN_ELAPSED_FOR_PROJECTION_SECONDS:
        return None
    eta_seconds = (100 - pct) / (pct / elapsed)
    seconds_to_reset = (reset_dt - now).total_seconds()
    if seconds_to_reset > 0 and eta_seconds > seconds_to_reset:
        return None
    return eta_seconds


def format_usage_constraint(usage_data, length=20):
    """Single usage bar for whichever window is closest to its cap."""
    from claude_tui_components.lines import build_bar_line

    if not usage_data:
        return ""
    key, window = _most_constraining_window(usage_data)
    if window is None:
        return ""
    pct = window["utilization"]
    ratio = min(pct / 100.0, 1.0)
    eta_seconds = _project_time_to_cap(key, pct, _parse_iso(window.get("resets_at", "")))

    if eta_seconds is not None:
        color = RED if ratio >= 0.8 else ORANGE if ratio >= 0.55 else YELLOW
        suffix = f"{color}~{_format_hm(eta_seconds)} to limit{RESET}"
    else:
        countdown = _format_reset_countdown(window.get("resets_at", ""))
        suffix = f"{GRAY}resets in {countdown}{RESET}" if countdown else ""

    return build_bar_line(ratio, length, pct_label=_CONSTRAINT_LABELS[key], suffix=suffix)'''

RENDER_MARKER = "format_usage_constraint"

OLD_RENDER_IMPORT = "from .api_clients import format_usage_session, format_usage_weekly"
NEW_RENDER_IMPORT = (
    OLD_RENDER_IMPORT + "\nfrom claude_tui_core.formatting import format_usage_constraint  # nix-darwin"
)

OLD_RENDER_COMPACT = '''    parts = []
    if is_visible("line1", "model"):
        parts.append(f"{BOLD}{MAGENTA}{ds.model}{RESET}")
    if is_visible("line1", "context_bar"):
        ctx = f"{ds.bar}"
        if is_visible("line1", "token_count"):
            ctx += f" {format_token_suffix(ds.tokens_str, ds.limit_str)}"
        parts.append(ctx)
    if ds.usage:
        session = format_usage_session(ds.usage, length=ds.bar_length)
        weekly = format_usage_weekly(ds.usage, length=ds.bar_length)
        if session:
            parts.append(session)
        if weekly:
            parts.append(weekly)'''

NEW_RENDER_COMPACT = '''    parts = []
    if is_visible("line1", "context_bar"):
        ctx = f"{ds.bar}"
        if is_visible("line1", "token_count"):
            ctx += f" {format_token_suffix(ds.tokens_str, ds.limit_str)}"
        parts.append(ctx)
    usage_str = format_usage_constraint(ds.usage, length=ds.bar_length)
    if usage_str:
        parts.append(usage_str)'''


def _apply_patch(target, marker, replacements, label):
    """Apply (old, new) replacements to target as one unit, gated by a single
    marker check so a multi-part patch can't half-apply."""
    try:
        with open(target, "r") as f:
            src = f.read()
    except OSError as e:
        print(f"WARNING: [claude-tui-usage-patch] could not read {target}: {e}", file=sys.stderr)
        return

    if marker in src:
        return

    if any(old not in src for old, _ in replacements):
        print(
            f"WARNING: [claude-tui-usage-patch] {label} anchor text not found in {target} "
            "(upstream claude-tui changed) -- skipping",
            file=sys.stderr,
        )
        return

    for old, new in replacements:
        src = src.replace(old, new)
    tmp = target + ".tmp"
    with open(tmp, "w") as f:
        f.write(src)
    os.replace(tmp, target)
    print(f"[claude-tui-usage-patch] {label} patched {target}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: claude-tui-usage-patch.py <libexec-dir>", file=sys.stderr)
        return 1

    libexec = sys.argv[1]
    _apply_patch(
        f"{libexec}/claude_tui_core/formatting.py",
        FORMATTING_MARKER,
        [(OLD_DATETIME_IMPORT, NEW_DATETIME_IMPORT), (OLD_FORMATTING_TAIL, NEW_FORMATTING_TAIL)],
        "usage widget (formatting.py)",
    )
    _apply_patch(
        f"{libexec}/claude-code-statusline/statusline_core/render.py",
        RENDER_MARKER,
        [(OLD_RENDER_IMPORT, NEW_RENDER_IMPORT), (OLD_RENDER_COMPACT, NEW_RENDER_COMPACT)],
        "compact line (render.py)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
