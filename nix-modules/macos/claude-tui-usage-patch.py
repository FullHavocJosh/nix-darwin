#!/usr/bin/env python3
"""Idempotent source patches for the claude-tui Homebrew formula (slima4/claude-tui).

Two independent, anchor-checked patches, applied by nix-darwin's activation
script every run (brew upgrades the formula in place, wiping any local edit
to the installed copy each time). Each is skipped (with a warning, no crash)
if its anchor text is missing, i.e. upstream changed the file it targets.

1. network.py / per-account usage cache: fetch_usage() cached Claude.ai's
   /api/oauth/usage response into a single ~/.claude/usage-cache.json shared
   by the whole $HOME. On a machine running more than one Claude Code account
   concurrently (e.g. a personal Claude.ai login alongside a work
   Enterprise/SSO account with no OAuth usage endpoint at all), that single
   shared file let one account's cached session/week numbers bleed into the
   other account's statusline instead of the widget just going blank for the
   account with no usage data. Patches fetch_usage() to key the cache file by
   a hash of the resolved token, and to return None (not a stale/foreign
   cache) when no token resolves at all.

2. formatting.py / most-constraining weekly window: format_usage_weekly()
   only ever rendered the "seven_day" field. The oauth/usage response also
   carries "seven_day_sonnet" (a narrower per-model cap) and "extra_usage"
   (purchased overage), either of which can bind before the plain weekly
   figure does — so a real, imminent constraint on one of those could go
   unshown. Patches format_usage_weekly() to render whichever of the three
   is currently closest to its cap. Superseded for actual rendering by
   patch 3 below; left in place (and still covered by upstream's own
   tests) since nothing else references it.

3. Combined single usage widget (formatting.py, network.py, api_clients.py,
   render.py): the statusline showed session (5-hour) and weekly usage as
   two separate bars with single-letter labels (S/W) and a bare reset-time
   countdown, which didn't say what window was being measured or give any
   sense of when a limit would actually be hit. Adds format_usage_constraint(),
   a single combined widget: whichever tracked window is currently closest
   to its cap, plainly labeled, with a linear projection of time-to-cap
   when one is computable (known fixed window length, reset timestamp
   present, usage trending upward, and projected to hit the cap before the
   window would reset anyway) — falling back to a plain "resets in <time>"
   otherwise. Rewires render.py's line 2, line 3, and compact-line builders
   to call it once instead of calling format_usage_session +
   format_usage_weekly separately.

4. Real constraint-window keys + local monthly cost + layout cleanup
   (transcript.py, formatting.py, display_state.py, render.py,
   statusline.py, new monthly_cost.py): patch 3 above originally tracked
   five_hour/seven_day/seven_day_sonnet/extra_usage, but reading
   code.claude.com/docs/en/statusline showed those last two are fields of
   the separate /api/oauth/usage HTTP response (network.py's fetch_usage())
   -- a function statusline.py's real render path never calls. The stdin
   `rate_limits` object Claude Code actually hands the statusline only ever
   carries five_hour, seven_day, and spend_limit (a work/gateway account's
   dollar-budget cap, Claude Code v2.1.251+). transcript.py's
   _build_usage_from_rate_limits() didn't pass spend_limit through at all,
   so a work account with a real $ budget cap had no way to show it even
   though Claude Code was already handing it over. Swaps the key set to the
   real three, adds a new monthly_cost.py module (a local $ estimate summed
   from this machine's own Claude Code session transcripts, priced through
   claude_tui_core.models' existing pricing table -- see that module's
   docstring for caveats), and reworks the compact line to drop the model
   name and append the monthly estimate after the usage widget.
"""

import sys

NETWORK_MARKER = "# nix-darwin: per-account usage cache patch"

OLD_IMPORTS = """import fcntl
import http.client
import json
import os
import ssl
import subprocess
import threading
import time
from typing import IO

from .settings import get_setting

# Paths
CLAUDE_DIR = ".claude"
STATUS_CACHE_PATH = os.path.join(
    os.path.expanduser("~"), CLAUDE_DIR, "api-status-cache.json"
)
STATUS_LOCK_PATH = STATUS_CACHE_PATH + ".lock"
USAGE_CACHE_PATH = os.path.join(os.path.expanduser("~"), CLAUDE_DIR, "usage-cache.json")
USAGE_LOCK_PATH = USAGE_CACHE_PATH + ".lock\""""

NEW_IMPORTS = f"""{NETWORK_MARKER}
import fcntl
import hashlib
import http.client
import json
import os
import ssl
import subprocess
import threading
import time
from typing import IO

from .settings import get_setting

# Paths
CLAUDE_DIR = ".claude"
STATUS_CACHE_PATH = os.path.join(
    os.path.expanduser("~"), CLAUDE_DIR, "api-status-cache.json"
)
STATUS_LOCK_PATH = STATUS_CACHE_PATH + ".lock"


def _usage_cache_paths(token: str) -> tuple[str, str]:
    \"\"\"Per-account cache path, keyed by a hash of the OAuth token.

    Multiple Claude Code accounts (e.g. personal vs an Enterprise/SSO org
    account) can run concurrently on this machine under the same $HOME. A
    single shared usage-cache.json would let one account's session/week
    numbers leak into the other account's statusline. Hashing the token
    keeps each account's cache isolated.
    \"\"\"
    h = hashlib.sha256(token.encode()).hexdigest()[:16]
    path = os.path.join(os.path.expanduser("~"), CLAUDE_DIR, f"usage-cache-{{h}}.json")
    return path, path + ".lock\""""

OLD_FETCH_USAGE = '''def fetch_usage(background=False):
    """Fetch usage data from Anthropic API."""
    if not get_setting("usage", "enabled", default=True):
        return None

    rate_limit = max(60, get_setting("usage", "rate_limit", default=60))
    cache = _read_json_file(USAGE_CACHE_PATH)
    now = time.time()

    if cache and now < cache.get("retry_after", 0):
        return cache

    is_stale = not cache or (now - cache.get("fetched_at", 0) >= rate_limit)

    if not is_stale:
        return cache

    if background:
        t = threading.Thread(
            target=fetch_usage, kwargs={"background": False}, daemon=True
        )
        t.start()
        return cache

    lock_fd = _try_acquire_lock(USAGE_LOCK_PATH)
    if lock_fd is None:
        return cache

    try:
        token = _load_oauth_token()
        if not token:
            return cache

        status, data = _fetch_https_json(
            "api.anthropic.com",
            "/api/oauth/usage",
            {
                "Accept": APPLICATION_JSON,
                "Authorization": f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
                "User-Agent": "claude-code/2.1.80",
            },
            timeout=3,
        )
        if status == 200 and data:
            fresh = _build_usage_cache(data)
            try:
                _write_json_file(USAGE_CACHE_PATH, fresh)
            except OSError:
                pass
            return fresh

        if status == 429:
            return _handle_usage_429(cache)
    finally:
        _release_lock(lock_fd)

    return cache'''

NEW_FETCH_USAGE = '''def fetch_usage(background=False):
    """Fetch usage data from Anthropic API."""
    if not get_setting("usage", "enabled", default=True):
        return None

    token = _load_oauth_token()
    if not token:
        # No resolvable OAuth token for this account/session (e.g. an
        # Enterprise/SSO or Bedrock/Vertex account with no Claude.ai usage
        # endpoint) -- return None rather than falling back to a cache file
        # that may belong to a different account. format_usage_session/
        # format_usage_weekly already render None as "", so the widget just
        # goes blank instead of showing another account's numbers.
        return None

    cache_path, lock_path = _usage_cache_paths(token)
    rate_limit = max(60, get_setting("usage", "rate_limit", default=60))
    cache = _read_json_file(cache_path)
    now = time.time()

    if cache and now < cache.get("retry_after", 0):
        return cache

    is_stale = not cache or (now - cache.get("fetched_at", 0) >= rate_limit)

    if not is_stale:
        return cache

    if background:
        t = threading.Thread(
            target=fetch_usage, kwargs={"background": False}, daemon=True
        )
        t.start()
        return cache

    lock_fd = _try_acquire_lock(lock_path)
    if lock_fd is None:
        return cache

    try:
        refreshed = _read_json_file(cache_path)
        if refreshed and now - refreshed.get("fetched_at", 0) < rate_limit:
            return refreshed

        status, data = _fetch_https_json(
            "api.anthropic.com",
            "/api/oauth/usage",
            {
                "Accept": APPLICATION_JSON,
                "Authorization": f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
                "User-Agent": "claude-code/2.1.80",
            },
            timeout=3,
        )
        if status == 200 and data:
            fresh = _build_usage_cache(data)
            try:
                _write_json_file(cache_path, fresh)
            except OSError:
                pass
            return fresh

        if status == 429:
            if not cache:
                cache = {"fetched_at": 0, "retry_count": 0, "retry_after": 0}
            current_retry = cache.get("retry_count", 0)
            backoff = min(120 * (2**current_retry), 600)
            cache["retry_count"] = current_retry + 1
            cache["retry_after"] = time.time() + backoff
            try:
                _write_json_file(cache_path, cache)
            except OSError:
                pass
            return cache
    finally:
        _release_lock(lock_fd)

    return cache'''


FORMATTING_MARKER = "# nix-darwin: most-constraining-weekly-window patch"

OLD_USAGE_BAR_FNS = '''def _format_usage_bar(usage_data, key, pct_label, length=20):
    """Format a usage window as a progress bar line."""
    from claude_tui_components.lines import build_bar_line

    if not usage_data:
        return ""
    window = usage_data.get(key, {})
    pct = window.get("utilization", 0)
    if pct is None:
        return ""

    ratio = min(pct / 100.0, 1.0)
    countdown = _format_reset_countdown(window.get("resets_at", ""))
    return build_bar_line(ratio, length, pct_label=pct_label, icon="⏱" if countdown else "", suffix=countdown)


def format_usage_session(usage_data, length=20):
    """Format session (5-hour) usage for display."""
    return _format_usage_bar(usage_data, "five_hour", "S", length)


def format_usage_weekly(usage_data, length=20):
    """Format weekly (7-day) usage for display."""
    return _format_usage_bar(usage_data, "seven_day", "W", length)'''

NEW_USAGE_BAR_FNS = f'''{FORMATTING_MARKER}
# seven_day is the plan-wide weekly cap; seven_day_sonnet and extra_usage are
# narrower windows the API also reports (Sonnet-specific cap, purchased
# overage) that can bind before the plain weekly figure does. Surfacing only
# seven_day meant a genuinely blocking constraint on one of the other two
# windows would never show up on the statusline until it already hit. Any
# key here not shaped like {{"utilization": <0-100>, ...}} is skipped rather
# than guessed at -- an unexpected response schema degrades to "ignored",
# never to a wrong number on screen.
_WEEKLY_CONSTRAINT_KEYS = ("seven_day", "seven_day_sonnet", "extra_usage")


def _most_constraining_window(usage_data, keys):
    """Pick whichever named usage window has the highest utilization."""
    best = None
    best_pct = -1
    for key in keys:
        window = usage_data.get(key)
        if not isinstance(window, dict):
            continue
        pct = window.get("utilization")
        if not isinstance(pct, (int, float)):
            continue
        if pct > best_pct:
            best_pct = pct
            best = window
    return best


def _format_usage_bar_from_window(window, pct_label, length=20):
    """Format a usage window dict as a progress bar line."""
    from claude_tui_components.lines import build_bar_line

    if not window:
        return ""
    pct = window.get("utilization", 0)
    if pct is None:
        return ""

    ratio = min(pct / 100.0, 1.0)
    countdown = _format_reset_countdown(window.get("resets_at", ""))
    return build_bar_line(ratio, length, pct_label=pct_label, icon="⏱" if countdown else "", suffix=countdown)


def format_usage_session(usage_data, length=20):
    """Format session (5-hour) usage for display."""
    if not usage_data:
        return ""
    return _format_usage_bar_from_window(usage_data.get("five_hour", {{}}), "S", length)


def format_usage_weekly(usage_data, length=20):
    """Format whichever weekly-ish usage window (seven_day, seven_day_sonnet,
    extra_usage) is currently closest to its cap."""
    if not usage_data:
        return ""
    window = _most_constraining_window(usage_data, _WEEKLY_CONSTRAINT_KEYS)
    return _format_usage_bar_from_window(window, "W", length) if window else ""'''

# --- Patch 3: single combined usage widget ---------------------------------

COMBINED_MARKER = "# nix-darwin: combined-usage-widget patch"

OLD_DATETIME_IMPORT = "from datetime import datetime, timezone"
NEW_DATETIME_IMPORT = "from datetime import datetime, timedelta, timezone"

# Anchored on format_usage_weekly's body as patch 2 left it -- patches apply
# in order, so this targets the post-patch-2 source, not the original.
OLD_TAIL_FOR_COMBINED = '''def format_usage_weekly(usage_data, length=20):
    """Format whichever weekly-ish usage window (seven_day, seven_day_sonnet,
    extra_usage) is currently closest to its cap."""
    if not usage_data:
        return ""
    window = _most_constraining_window(usage_data, _WEEKLY_CONSTRAINT_KEYS)
    return _format_usage_bar_from_window(window, "W", length) if window else ""'''

NEW_TAIL_FOR_COMBINED = OLD_TAIL_FOR_COMBINED + '''


''' + COMBINED_MARKER + '''
# Single combined usage widget: one %, plainly labeled with which window it
# is, and (when computable) a projected time to hitting that window's cap --
# replacing the separate S/W bars, which gave no sense of what was being
# measured or when it would actually bind. format_usage_session/
# format_usage_weekly above are left in place (still covered by upstream's
# own tests) but are no longer called from render.py after this patch.
_CONSTRAINT_LABELS = {
    "five_hour": "5-hour",
    "seven_day": "7-day",
    "seven_day_sonnet": "7-day (Sonnet)",
    "extra_usage": "Overage",
}

# Fixed, documented window lengths for Claude's rate-limit windows, used to
# project "time until this window hits its cap" from a single utilization%
# reading. extra_usage has no documented fixed window length (it may be a
# purchased balance with no rolling reset) so it's deliberately absent here:
# no projection is attempted for it, only the plain percentage.
_CONSTRAINT_WINDOW_SECONDS = {
    "five_hour": 5 * 3600,
    "seven_day": 7 * 86400,
    "seven_day_sonnet": 7 * 86400,
}

_ALL_CONSTRAINT_KEYS = ("five_hour", "seven_day", "seven_day_sonnet", "extra_usage")


def _most_constraining_window_and_key(usage_data, keys):
    """Like _most_constraining_window, but also returns which key won."""
    best_key, best, best_pct = None, None, -1
    for key in keys:
        window = usage_data.get(key)
        if not isinstance(window, dict):
            continue
        pct = window.get("utilization")
        if not isinstance(pct, (int, float)):
            continue
        if pct > best_pct:
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


# Minimum time into a window before trusting a linear-rate projection. Right
# after a window resets, elapsed is tiny, so even trivial usage produces a
# wildly inflated rate estimate (e.g. 1% two minutes in projects hitting the
# cap in the next few minutes) -- a false alarm, not a real constraint.
_MIN_ELAPSED_FOR_PROJECTION_SECONDS = 300


def _project_time_to_cap(key, pct, reset_dt):
    """Linear projection of when this window's usage would hit 100%, from
    its known fixed duration and current utilization. None when: unknown
    window duration, no reset timestamp, not enough elapsed time yet for a
    stable rate estimate, usage isn't trending upward, or the window would
    reset before the cap is reached."""
    duration = _CONSTRAINT_WINDOW_SECONDS.get(key)
    if duration is None or reset_dt is None or pct is None or pct <= 0:
        return None
    now = datetime.now(timezone.utc)
    window_start = reset_dt - timedelta(seconds=duration)
    elapsed = (now - window_start).total_seconds()
    if elapsed < _MIN_ELAPSED_FOR_PROJECTION_SECONDS:
        return None
    rate = pct / elapsed
    if rate <= 0:
        return None
    eta_seconds = (100 - pct) / rate
    seconds_to_reset = (reset_dt - now).total_seconds()
    if seconds_to_reset > 0 and eta_seconds > seconds_to_reset:
        return None
    return eta_seconds


def format_usage_constraint(usage_data, length=20):
    """Single combined usage widget: whichever tracked window (5-hour
    session, 7-day, 7-day Sonnet-only, purchased overage) is currently
    closest to its cap -- one %, plainly labeled with which window it is,
    and a projected time to hitting that cap when one can be computed."""
    from claude_tui_components.lines import build_bar_line

    if not usage_data:
        return ""
    key, window = _most_constraining_window_and_key(usage_data, _ALL_CONSTRAINT_KEYS)
    if window is None:
        return ""
    pct = window.get("utilization")
    if not isinstance(pct, (int, float)):
        return ""

    ratio = min(pct / 100.0, 1.0)
    label = _CONSTRAINT_LABELS.get(key, key)
    reset_dt = _parse_iso(window.get("resets_at", ""))
    eta_seconds = _project_time_to_cap(key, pct, reset_dt)

    if eta_seconds is not None:
        color = RED if ratio >= 0.8 else ORANGE if ratio >= 0.55 else YELLOW
        suffix = f"{color}~{_format_hm(eta_seconds)} to limit{RESET}"
    else:
        countdown = _format_reset_countdown(window.get("resets_at", ""))
        suffix = f"{GRAY}resets in {countdown}{RESET}" if countdown else ""

    return build_bar_line(ratio, length, pct_label=label, suffix=suffix)'''

OLD_API_CLIENTS = '''from claude_tui_core.network import (
    fetch_api_status,
    format_api_status,
    fetch_usage,
    format_usage_session,
    format_usage_weekly,
)

__all__ = [
    "fetch_api_status",
    "format_api_status",
    "fetch_usage",
    "format_usage_session",
    "format_usage_weekly",
]'''

NEW_API_CLIENTS = '''from claude_tui_core.network import (
    fetch_api_status,
    format_api_status,
    fetch_usage,
    format_usage_session,
    format_usage_weekly,
    format_usage_constraint,
)

__all__ = [
    "fetch_api_status",
    "format_api_status",
    "fetch_usage",
    "format_usage_session",
    "format_usage_weekly",
    "format_usage_constraint",
]'''

OLD_NETWORK_REEXPORT = '''from .formatting import (  # noqa: E402
    format_api_status,
    format_usage_session,
    format_usage_weekly,
)'''

NEW_NETWORK_REEXPORT = '''from .formatting import (  # noqa: E402
    format_api_status,
    format_usage_session,
    format_usage_weekly,
    format_usage_constraint,
)'''

OLD_RENDER_IMPORT = "from .api_clients import format_usage_session, format_usage_weekly"
NEW_RENDER_IMPORT = "from .api_clients import format_usage_constraint"

OLD_RENDER_LINE2 = '''    if is_visible("line2", "usage"):
        usage_str = format_usage_session(ds.usage, length=ds.bar_length)
        if usage_str:
            parts.append(usage_str)'''

NEW_RENDER_LINE2 = '''    if is_visible("line2", "usage"):
        usage_str = format_usage_constraint(ds.usage, length=ds.bar_length)
        if usage_str:
            parts.append(usage_str)'''

OLD_RENDER_LINE3 = '''    lines = []
    if is_visible("line3", "usage_weekly"):
        weekly_str = format_usage_weekly(ds.usage, length=ds.bar_length)
        if weekly_str:
            lines.append(weekly_str)
    wrapped = wrap_line_parts('''

NEW_RENDER_LINE3 = '''    lines = []
    wrapped = wrap_line_parts('''

OLD_RENDER_COMPACT = '''    if ds.usage:
        session = format_usage_session(ds.usage, length=ds.bar_length)
        weekly = format_usage_weekly(ds.usage, length=ds.bar_length)
        if session:
            parts.append(session)
        if weekly:
            parts.append(weekly)'''

NEW_RENDER_COMPACT = '''    if ds.usage:
        usage_str = format_usage_constraint(ds.usage, length=ds.bar_length)
        if usage_str:
            parts.append(usage_str)'''

# --- Patch 4: real constraint-window keys + local monthly cost + layout ----

OLD_TRANSCRIPT_KEYS = '''    for key in ("five_hour", "seven_day"):'''
NEW_TRANSCRIPT_KEYS = '''    for key in ("five_hour", "seven_day", "spend_limit"):'''

OLD_REAL_KEYS_BLOCK = '''# nix-darwin: combined-usage-widget patch
# Single combined usage widget: one %, plainly labeled with which window it
# is, and (when computable) a projected time to hitting that window's cap --
# replacing the separate S/W bars, which gave no sense of what was being
# measured or when it would actually bind. format_usage_session/
# format_usage_weekly above are left in place (still covered by upstream's
# own tests) but are no longer called from render.py after this patch.
_CONSTRAINT_LABELS = {
    "five_hour": "5-hour",
    "seven_day": "7-day",
    "seven_day_sonnet": "7-day (Sonnet)",
    "extra_usage": "Overage",
}

# Fixed, documented window lengths for Claude's rate-limit windows, used to
# project "time until this window hits its cap" from a single utilization%
# reading. extra_usage has no documented fixed window length (it may be a
# purchased balance with no rolling reset) so it's deliberately absent here:
# no projection is attempted for it, only the plain percentage.
_CONSTRAINT_WINDOW_SECONDS = {
    "five_hour": 5 * 3600,
    "seven_day": 7 * 86400,
    "seven_day_sonnet": 7 * 86400,
}

_ALL_CONSTRAINT_KEYS = ("five_hour", "seven_day", "seven_day_sonnet", "extra_usage")'''

NEW_REAL_KEYS_BLOCK = '''# nix-darwin: combined-usage-widget patch
# Single combined usage widget: one %, plainly labeled with which window it
# is, and (when computable) a projected time to hitting that window's cap --
# replacing the separate S/W bars, which gave no sense of what was being
# measured or when it would actually bind. format_usage_session/
# format_usage_weekly above are left in place (still covered by upstream's
# own tests) but are no longer called from render.py after this patch.
#
# Key set corrected 2026-09-21 after reading code.claude.com/docs/en/statusline:
# the real stdin `rate_limits` object Claude Code hands the statusline only
# ever carries five_hour, seven_day, and spend_limit (the last one only
# "behind a Claude apps gateway that sets a spend limit for you", Claude Code
# v2.1.251+) -- seven_day_sonnet/extra_usage were fields of the separate
# /api/oauth/usage HTTP response that fetch_usage() (network.py) calls, but
# that function is never actually invoked by statusline.py's real render
# path, so those two keys could never appear in practice. spend_limit is the
# real mechanism for a work/gateway account's dollar-budget cap.
_CONSTRAINT_LABELS = {
    "five_hour": "5-hour",
    "seven_day": "7-day",
    "spend_limit": "Spend limit",
}

# Fixed, documented window lengths for Claude's rate-limit windows, used to
# project "time until this window hits its cap" from a single utilization%
# reading. spend_limit's reset period is gateway-configured, not a documented
# fixed duration, so it's deliberately absent here: no projection is
# attempted for it, only the plain percentage (which can exceed 100 -- see
# format_usage_constraint).
_CONSTRAINT_WINDOW_SECONDS = {
    "five_hour": 5 * 3600,
    "seven_day": 7 * 86400,
}

_ALL_CONSTRAINT_KEYS = ("five_hour", "seven_day", "spend_limit")'''

OLD_DISPLAY_STATE = '''    cache_pct: int = 0
    cost_per_turn: str = ""

    # Layout
    bar_length: int = 20'''

NEW_DISPLAY_STATE = '''    cache_pct: int = 0
    cost_per_turn: str = ""
    monthly_cost_part: str = ""

    # Layout
    bar_length: int = 20'''

OLD_COMPACT_LINE_V2 = '''def build_compact_line(ds):
    """Build compact single-line from DisplayState."""
    parts = []
    if is_visible("line1", "model"):
        parts.append(f"{BOLD}{MAGENTA}{ds.model}{RESET}")
    if is_visible("line1", "context_bar"):
        ctx = f"{ds.bar}"
        if is_visible("line1", "token_count"):
            ctx += f" {format_token_suffix(ds.tokens_str, ds.limit_str)}"
        parts.append(ctx)
    if ds.usage:
        usage_str = format_usage_constraint(ds.usage, length=ds.bar_length)
        if usage_str:
            parts.append(usage_str)
    sep = f" {GRAY}⋮{RESET} "
    return sep.join(parts) if parts else ""'''

NEW_COMPACT_LINE_V2 = '''def build_compact_line(ds):
    """Build compact single-line from DisplayState.

    nix-darwin: drops the model name (redundant with what's visible
    elsewhere in the UI per user request) and appends a local monthly-cost
    estimate after the usage widget."""
    parts = []
    if is_visible("line1", "context_bar"):
        ctx = f"{ds.bar}"
        if is_visible("line1", "token_count"):
            ctx += f" {format_token_suffix(ds.tokens_str, ds.limit_str)}"
        parts.append(ctx)
    if ds.usage:
        usage_str = format_usage_constraint(ds.usage, length=ds.bar_length)
        if usage_str:
            if ds.monthly_cost_part:
                usage_str += f" {GRAY}·{RESET} {ds.monthly_cost_part}"
            parts.append(usage_str)
    elif ds.monthly_cost_part:
        parts.append(ds.monthly_cost_part)
    sep = f" {GRAY}⋮{RESET} "
    return sep.join(parts) if parts else ""'''

OLD_STATUSLINE_IMPORT = '''from statusline_core.transcript import (
    parse_input_data,
    parse_transcript,
)
from claude_tui_components.utils import format_tokens'''

NEW_STATUSLINE_IMPORT = '''from statusline_core.transcript import (
    parse_input_data,
    parse_transcript,
)
from claude_tui_components.utils import format_tokens
from claude_tui_core.monthly_cost import fetch_monthly_cost, format_monthly_cost'''

OLD_STATUSLINE_COMPUTE = '''    usage = basic["usage"]

    ds = DisplayState('''

NEW_STATUSLINE_COMPUTE = '''    usage = basic["usage"]
    monthly_cost_part = format_monthly_cost(fetch_monthly_cost(background=True))

    ds = DisplayState('''

OLD_STATUSLINE_WIRING = '''        cost_per_turn=calculate_cost_per_turn(cost, metrics["turn_count"]),
        bar_length=bar_length,
    )'''

NEW_STATUSLINE_WIRING = '''        cost_per_turn=calculate_cost_per_turn(cost, metrics["turn_count"]),
        bar_length=bar_length,
        monthly_cost_part=monthly_cost_part,
    )'''

MONTHLY_COST_MODULE_SOURCE = '''# nix-darwin: local-monthly-cost patch
"""Local monthly-cost estimate for the statusline.

Not a real billed total -- there is no local API for that (Anthropic's
Usage & Cost Admin API and the Claude Enterprise Analytics API both require
an org admin credential this account may not have). This instead recomputes
an estimate from this machine's own Claude Code session transcripts: sums
each session ending in the current UTC calendar month, using each session's
own token counts priced through claude_tui_core.models' pricing table --
the same list-price convention claude-code-session-stats already uses for
its own per-session cost breakdown.

Caveats, worth surfacing to the user:
- Local-machine only. Doesn't see sessions run on another device, or any
  Console/API usage outside Claude Code.
- Doesn't distinguish which Claude account was active per session --
  personal and work usage on the same machine get summed together.
- List-price estimate. For a Pro/Max/Enterprise seat this isn't what's
  actually billed (flat subscription, not per-token); for a gateway/API
  account it should track real spend reasonably closely.
- A session that started last month and continued into this one has its
  *entire* cost attributed to whichever month its last message landed in
  (matching the granularity claude-code-session-stats already uses).
"""

import importlib.util
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .network import _read_json_file, _write_json_file, _try_acquire_lock, _release_lock
from .settings import get_setting

CLAUDE_DIR = ".claude"
MONTHLY_COST_CACHE_PATH = os.path.join(os.path.expanduser("~"), CLAUDE_DIR, "monthly-cost-cache.json")
MONTHLY_COST_LOCK_PATH = MONTHLY_COST_CACHE_PATH + ".lock"

# claude_tui_core/monthly_cost.py -> libexec/claude_tui_core/.. -> libexec/
_SESSION_STATS_PATH = (
    Path(__file__).resolve().parent.parent / "claude-code-session-stats" / "session-stats.py"
)

_session_stats_module = None
_session_stats_load_failed = False


def _load_session_stats_module():
    """Dynamically load the sibling session-stats.py script as a module.

    It's a standalone script (hyphenated dir/file names, not a package), so
    it's loaded by path rather than imported by name -- the same pattern
    settings.py's load_widget already uses for widget files.
    """
    global _session_stats_module, _session_stats_load_failed
    if _session_stats_module is not None:
        return _session_stats_module
    if _session_stats_load_failed:
        return None
    if not _SESSION_STATS_PATH.exists():
        _session_stats_load_failed = True
        return None
    try:
        spec = importlib.util.spec_from_file_location("claude_code_session_stats", _SESSION_STATS_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        _session_stats_load_failed = True
        return None
    _session_stats_module = mod
    return mod


def _current_month_key(now=None):
    now = now or datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def _compute_monthly_cost():
    mod = _load_session_stats_module()
    if mod is None:
        return None

    month_key = _current_month_key()
    total = 0.0
    try:
        sessions = mod.find_sessions(days=32)
    except Exception:
        return None

    for s in sessions:
        try:
            report = mod.parse_session(s["path"])
        except Exception:
            continue
        end_time = report.get("end_time")
        if not end_time:
            continue
        try:
            end_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))
        except ValueError:
            continue
        if _current_month_key(end_dt) != month_key:
            continue
        total += report.get("cost", {}).get("total", 0.0)

    return total


def fetch_monthly_cost(background=False):
    """Cached local monthly-cost estimate. Returns a float, or None when
    disabled, unavailable (session-stats.py missing), or never yet computed
    and a background refresh was just kicked off."""
    if not get_setting("monthly_cost", "enabled", default=True):
        return None

    ttl = max(300, get_setting("monthly_cost", "ttl", default=900))
    cache = _read_json_file(MONTHLY_COST_CACHE_PATH)
    now = time.time()
    month_key = _current_month_key()

    is_stale = (
        not cache
        or cache.get("month") != month_key
        or now - cache.get("fetched_at", 0) >= ttl
    )
    if not is_stale:
        return cache.get("total")

    if background:
        t = threading.Thread(target=fetch_monthly_cost, kwargs={"background": False}, daemon=True)
        t.start()
        return cache.get("total") if cache and cache.get("month") == month_key else None

    lock_fd = _try_acquire_lock(MONTHLY_COST_LOCK_PATH)
    if lock_fd is None:
        return cache.get("total") if cache else None

    try:
        refreshed = _read_json_file(MONTHLY_COST_CACHE_PATH)
        if refreshed and refreshed.get("month") == month_key and now - refreshed.get("fetched_at", 0) < ttl:
            return refreshed.get("total")

        total = _compute_monthly_cost()
        if total is None:
            return cache.get("total") if cache and cache.get("month") == month_key else None

        fresh = {"fetched_at": now, "month": month_key, "total": total}
        try:
            _write_json_file(MONTHLY_COST_CACHE_PATH, fresh)
        except OSError:
            pass
        return total
    finally:
        _release_lock(lock_fd)


def format_monthly_cost(total):
    """Format a monthly-cost float as a compact '$X.XX/mo' suffix, or ''."""
    if total is None:
        return ""
    from .formatting import GRAY, RESET

    return f"{GRAY}${total:.2f}/mo{RESET}"
'''


def _apply_patch(target, marker, replacements, label):
    """Apply one or more (old, new) replacements to target as a single unit,
    gated by one marker check so a multi-part patch can't apply half of
    itself (idempotency marker only appears in one of the replacements)."""
    try:
        with open(target, "r") as f:
            src = f.read()
    except OSError as e:
        print(f"WARNING: [claude-tui-usage-patch] could not read {target}: {e}", file=sys.stderr)
        return

    if marker in src:
        print(f"[claude-tui-usage-patch] {label} already applied")
        return

    missing = [old for old, _ in replacements if old not in src]
    if missing:
        print(
            f"WARNING: [claude-tui-usage-patch] {label} anchor text not found in {target} "
            "(upstream claude-tui changed) -- skipping",
            file=sys.stderr,
        )
        return

    patched = src
    for old, new in replacements:
        patched = patched.replace(old, new)
    tmp = target + ".tmp"
    with open(tmp, "w") as f:
        f.write(patched)
    import os as _os

    _os.replace(tmp, target)
    print(f"[claude-tui-usage-patch] {label} patched {target}")

def _ensure_file(target, content, label):
    """Write content to target if it's not already there. For a brand-new
    file wholly owned by this patch script (nothing to merge with upstream
    changes), so an idempotent overwrite is simpler than an anchor check."""
    try:
        with open(target, "r") as f:
            if f.read() == content:
                print(f"[claude-tui-usage-patch] {label} already up to date")
                return
    except OSError:
        pass
    tmp = target + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    import os as _os

    _os.replace(tmp, target)
    print(f"[claude-tui-usage-patch] {label} wrote {target}")



def main() -> int:
    if len(sys.argv) != 2:
        print("usage: claude-tui-usage-patch.py <libexec-dir>", file=sys.stderr)
        return 1

    libexec = sys.argv[1]
    _apply_patch(
        f"{libexec}/claude_tui_core/network.py",
        NETWORK_MARKER,
        [(OLD_IMPORTS, NEW_IMPORTS), (OLD_FETCH_USAGE, NEW_FETCH_USAGE)],
        "per-account cache",
    )
    _apply_patch(
        f"{libexec}/claude_tui_core/formatting.py",
        FORMATTING_MARKER,
        [(OLD_USAGE_BAR_FNS, NEW_USAGE_BAR_FNS)],
        "most-constraining weekly window",
    )
    _apply_patch(
        f"{libexec}/claude_tui_core/formatting.py",
        COMBINED_MARKER,
        [(OLD_DATETIME_IMPORT, NEW_DATETIME_IMPORT), (OLD_TAIL_FOR_COMBINED, NEW_TAIL_FOR_COMBINED)],
        "combined usage widget (formatting.py)",
    )
    _apply_patch(
        f"{libexec}/claude_tui_core/network.py",
        "format_usage_constraint",
        [(OLD_NETWORK_REEXPORT, NEW_NETWORK_REEXPORT)],
        "combined usage widget (network.py re-export)",
    )
    _apply_patch(
        f"{libexec}/claude-code-statusline/statusline_core/api_clients.py",
        "format_usage_constraint",
        [(OLD_API_CLIENTS, NEW_API_CLIENTS)],
        "combined usage widget (api_clients.py re-export)",
    )
    _apply_patch(
        f"{libexec}/claude-code-statusline/statusline_core/render.py",
        "format_usage_constraint",
        [
            (OLD_RENDER_IMPORT, NEW_RENDER_IMPORT),
            (OLD_RENDER_LINE2, NEW_RENDER_LINE2),
            (OLD_RENDER_LINE3, NEW_RENDER_LINE3),
            (OLD_RENDER_COMPACT, NEW_RENDER_COMPACT),
        ],
        "combined usage widget (render.py)",
    )
    _apply_patch(
        f"{libexec}/claude-code-statusline/statusline_core/transcript.py",
        "spend_limit",
        [(OLD_TRANSCRIPT_KEYS, NEW_TRANSCRIPT_KEYS)],
        "real constraint keys (transcript.py spend_limit passthrough)",
    )
    _apply_patch(
        f"{libexec}/claude_tui_core/formatting.py",
        '"spend_limit": "Spend limit"',
        [(OLD_REAL_KEYS_BLOCK, NEW_REAL_KEYS_BLOCK)],
        "real constraint keys (formatting.py)",
    )
    _ensure_file(
        f"{libexec}/claude_tui_core/monthly_cost.py",
        MONTHLY_COST_MODULE_SOURCE,
        "monthly cost module",
    )
    _apply_patch(
        f"{libexec}/claude-code-statusline/statusline_core/display_state.py",
        "monthly_cost_part",
        [(OLD_DISPLAY_STATE, NEW_DISPLAY_STATE)],
        "monthly cost (display_state.py field)",
    )
    _apply_patch(
        f"{libexec}/claude-code-statusline/statusline_core/render.py",
        "monthly_cost_part",
        [(OLD_COMPACT_LINE_V2, NEW_COMPACT_LINE_V2)],
        "monthly cost + drop model (render.py compact line)",
    )
    _apply_patch(
        f"{libexec}/claude-code-statusline/statusline.py",
        "fetch_monthly_cost",
        [
            (OLD_STATUSLINE_IMPORT, NEW_STATUSLINE_IMPORT),
            (OLD_STATUSLINE_COMPUTE, NEW_STATUSLINE_COMPUTE),
            (OLD_STATUSLINE_WIRING, NEW_STATUSLINE_WIRING),
        ],
        "monthly cost (statusline.py wiring)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
