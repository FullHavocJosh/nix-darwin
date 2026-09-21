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
   is currently closest to its cap.
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
