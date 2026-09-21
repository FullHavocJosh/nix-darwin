#!/usr/bin/env python3
"""Idempotent source patch for the claude-tui Homebrew formula (slima4/claude-tui).

claude_tui_core/network.py fetches Claude.ai's /api/oauth/usage endpoint into
a single ~/.claude/usage-cache.json shared by the whole $HOME. On a machine
that runs more than one Claude Code account concurrently (e.g. a personal
Claude.ai login alongside a work Enterprise/SSO account that has no OAuth
usage endpoint at all), that single shared file lets one account's cached
session/week numbers bleed into the other account's statusline instead of
the widget just going blank for the account that has no usage data.

This patches fetch_usage() to key the cache file by a hash of the resolved
token (so concurrent accounts get separate cache files) and to return None —
not a stale/foreign cache — when no token can be resolved at all, which the
existing format_usage_session/format_usage_weekly already render as "".

Applied by nix-darwin's activation script every run (brew upgrades the
formula in place, wiping any local edit to the installed copy each time).
Anchored on the exact current upstream source; if the anchor text is missing
(upstream changed the file), this exits without modifying anything and warns
the caller to re-check.
"""

import sys

MARKER = "# nix-darwin: per-account usage cache patch"

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

NEW_IMPORTS = f"""{MARKER}
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


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: claude-tui-usage-patch.py <libexec-dir>", file=sys.stderr)
        return 1

    target = f"{sys.argv[1]}/claude_tui_core/network.py"
    try:
        with open(target, "r") as f:
            src = f.read()
    except OSError as e:
        print(f"WARNING: [claude-tui-usage-patch] could not read {target}: {e}", file=sys.stderr)
        return 0

    if MARKER in src:
        print("[claude-tui-usage-patch] already applied")
        return 0

    if OLD_IMPORTS not in src or OLD_FETCH_USAGE not in src:
        print(
            f"WARNING: [claude-tui-usage-patch] anchor text not found in {target} "
            "(upstream claude-tui changed) -- skipping, statusline usage cache is unpatched",
            file=sys.stderr,
        )
        return 0

    patched = src.replace(OLD_IMPORTS, NEW_IMPORTS).replace(OLD_FETCH_USAGE, NEW_FETCH_USAGE)
    tmp = target + ".tmp"
    with open(tmp, "w") as f:
        f.write(patched)
    import os as _os

    _os.replace(tmp, target)
    print(f"[claude-tui-usage-patch] patched {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
