#!/usr/bin/env python3
"""aidev's remote builder: the 30B coder model served by an OpenAI-compatible llama-server on another
machine (the G14), so the local one need not be loaded.

On by default: with nothing configured url() is the default server (https://llm.rollet.family/v1) and
the key is fetched from Doppler at runtime (LLM_PUBLIC_API_KEY, FullHavocJosh / root_hetzner-cluster),
so no env setup is needed; AIDEV_REMOTE_BUILDER=off (or "0", "no", "false") turns those defaults off,
while an explicit AIDEV_REMOTE_BUILDER_URL (an OpenAI base such as http://HOST:8082/v1) still wins, off
or not. The key resolves in order: AIDEV_REMOTE_BUILDER_KEY_FILE, AIDEV_REMOTE_BUILDER_KEY, then
Doppler, whose result is cached, failures included, so the mid-job monitor never calls it twice.
probe() checks in under timeout + 0.5 s that the server answers /models with the model alias
(qwen3-coder-30b, or AIDEV_REMOTE_BUILDER_MODEL); models_config(ctx) is then the pi models.json dict
that points provider `coder` at it. The key never appears in models.json or anything else this module
returns: apiKey is "!cat <file>", the configured key file or a 0600 temp file this module writes the
key into and removes at exit, so pi reads it at runtime. Failure reasons are short fixed words
("timeout", "refused", "http 401") that never contain the URL, host or key, because the driver prints
them with note() as it falls through to the local 30B, then Zen.

The remote path skips the local edit.lock and the 2-minute idle unload: that machine owns its model.
With the off switch set and no explicit URL, configured() is False and nothing changes. Stdlib only.
"""

import atexit
import json
import os
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

URL_ENV = "AIDEV_REMOTE_BUILDER_URL"  # an OpenAI base, such as http://HOST:8082/v1
KEY_FILE_ENV = (
    "AIDEV_REMOTE_BUILDER_KEY_FILE"  # the file the server's bearer key lives in
)
KEY_ENV = (
    "AIDEV_REMOTE_BUILDER_KEY"  # the bearer key itself, when no key file is at hand
)
OFF_ENV = "AIDEV_REMOTE_BUILDER"  # "off", "0", "no" or "false" disables the defaults
MODEL_ENV = "AIDEV_REMOTE_BUILDER_MODEL"  # overrides DEFAULT_ALIAS
DEFAULT_URL = (
    "https://llm.rollet.family/v1"  # the server used when no URL is configured
)
DEFAULT_ALIAS = "qwen3-coder-30b"
DEVICE_ENV = "LLM_DEVICE"  # the device name in the gateway key table, e.g. MACBOOK_M2PRO; picks LLM_KEY_<NAME>
DEVICE_KEY_FILE = "~/.config/llm-gateway/key"  # default per-device key file (0600), read before Doppler
TIERS_URL = "https://llm.rollet.family/auto/v1/tiers"
PROBE_TIMEOUT_S = 2.0
MAX_TOKENS = 8192

_KEY_CACHE = {}  # doppler_key()'s cached result, None included, keyed "doppler"
_TMP_KEY_PATH = (
    None  # the 0600 temp file key_path() writes the key into, removed at exit
)


def off():
    """True when AIDEV_REMOTE_BUILDER disables the remote builder defaults."""
    return os.environ.get(OFF_ENV, "").strip().lower() in ("off", "0", "no", "false")


def url():
    """The OpenAI base to use, without a trailing slash: AIDEV_REMOTE_BUILDER_URL when set (it wins
    even when off), else '' when the defaults are off, else the default URL."""
    explicit = os.environ.get(URL_ENV, "").strip().rstrip("/")
    if explicit:
        return explicit
    return "" if off() else DEFAULT_URL


def key_file():
    """The configured key file path; '' when unset."""
    return os.environ.get(KEY_FILE_ENV, "").strip()


def alias():
    """The remote model's id: AIDEV_REMOTE_BUILDER_MODEL, or the default qwen3-coder-30b."""
    return os.environ.get(MODEL_ENV, "").strip() or DEFAULT_ALIAS


def configured():
    """True when a URL is in play, explicit or default; the key is resolved later, from a key file,
    the env or Doppler, so this call never runs Doppler."""
    return bool(url())


def read_key():
    """The bearer key: the key file's stripped contents when one is configured (None when it cannot
    be read), else AIDEV_REMOTE_BUILDER_KEY when non-empty, else the Doppler key (None when that
    failed)."""
    if key_file():
        try:
            with open(key_file()) as fh:
                return fh.read().strip()
        except OSError:
            return None
    env_key = os.environ.get(KEY_ENV, "").strip()
    if env_key:
        return env_key
    try:
        with open(os.path.expanduser(DEVICE_KEY_FILE)) as fh:
            file_key = fh.read().strip()
        if file_key:
            return file_key
    except OSError:
        pass
    return doppler_key()


def doppler_key():
    """The LLM_PUBLIC_API_KEY secret from Doppler (FullHavocJosh / root_hetzner-cluster), or None
    when the doppler CLI is missing, errors or is slow. The result is cached, None included, so the
    mid-job monitor never runs Doppler twice; the key is never printed or logged."""
    if "doppler" in _KEY_CACHE:
        return _KEY_CACHE["doppler"]
    key = None
    device = os.environ.get(DEVICE_ENV, "").strip().upper().replace("-", "_")
    names = (["LLM_KEY_" + device] if device else []) + ["LLM_PUBLIC_API_KEY"]
    for name in names:  # the per-device key first, then the shared key
        try:
            proc = subprocess.run(
                [
                    "doppler",
                    "secrets",
                    "get",
                    name,
                    "--project",
                    "FullHavocJosh",
                    "--config",
                    "root_hetzner-cluster",
                    "--plain",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                key = proc.stdout.strip()
                break
        except (OSError, subprocess.TimeoutExpired):
            continue
    _KEY_CACHE["doppler"] = key
    return key


def reset_key_cache():
    """Clear doppler_key()'s cache so the next call runs Doppler again; tests call it."""
    _KEY_CACHE.clear()


def key_path():
    """The file pi reads the key from at runtime: key_file() when one is configured, else the 0600
    temp file this process wrote read_key() into (created once, removed at exit); None when there is
    no key."""
    global _TMP_KEY_PATH
    if key_file():
        return key_file()
    if _TMP_KEY_PATH:
        return _TMP_KEY_PATH
    key = read_key()
    if key is None:
        return None
    fd, path = tempfile.mkstemp(prefix="aidev-remote-key-")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(key)
    except OSError:
        try:
            os.unlink(path)
        except OSError:
            pass
        return None
    _TMP_KEY_PATH = path
    return path


def _remove_tmp_key():
    """The atexit hook that removes the temp key file, if this process created one."""
    global _TMP_KEY_PATH
    if _TMP_KEY_PATH:
        try:
            os.unlink(_TMP_KEY_PATH)
        except OSError:
            pass
        _TMP_KEY_PATH = None


atexit.register(_remove_tmp_key)


def _short_reason(err):
    """One short fixed word for what went wrong; never the URL, host or key, whatever the exception says."""
    if isinstance(err, TimeoutError):
        return "timeout"
    if isinstance(err, ConnectionRefusedError):
        return "refused"
    code = getattr(err, "code", None)
    return f"http {code}" if isinstance(code, int) else "unreachable"


def probe(timeout=PROBE_TIMEOUT_S):
    """(ok, reason): GET <url>/models with the bearer key, one attempt. ok only on HTTP 200 whose data list
    holds the alias; every failure gets a short reason with no URL, host or key in it."""
    base, key = url(), read_key()
    if not base:
        return False, "not configured"
    if key is None:
        return False, ("no key file" if key_file() else "no key")
    req = urllib.request.Request(
        base + "/models", headers={"Authorization": "Bearer " + key}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.getcode()
            data = json.load(r)
    except urllib.error.HTTPError as e:
        return False, f"http {e.code}"
    except urllib.error.URLError as e:
        return False, _short_reason(e.reason)
    except TimeoutError:
        return False, "timeout"
    except ValueError:
        return False, "bad response"
    except OSError:
        return False, "unreachable"
    if status != 200:
        return False, f"http {status}"
    listed = data.get("data") if isinstance(data, dict) else None
    if isinstance(listed, list) and any(
        isinstance(m, dict) and m.get("id") == alias() for m in listed
    ):
        return True, ""
    return False, "model not listed"


def gateway_pool(timeout=PROBE_TIMEOUT_S):
    """{backend id: {"healthy", "window", "rank", "model"}} for every backend in GET /auto/v1/tiers, or None when
    the gateway, the key or the answer fails. Never raises; the key is never printed."""
    key = read_key()
    if not key:
        return None
    req = urllib.request.Request(TIERS_URL, headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        out = {}
        for backends in data["groups"].values():
            for b in backends:
                out.setdefault(b["id"], {"healthy": bool(b["healthy"]), "window": int(b.get("window") or 0),
                                         "rank": b.get("rank"), "model": b.get("model", "")})
        return out
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def gateway_health(timeout=PROBE_TIMEOUT_S):
    """{backend id: healthy} from gateway_pool(), or None when the gateway cannot be read."""
    pool = gateway_pool(timeout)
    return None if pool is None else {k: v["healthy"] for k, v in pool.items()}


def models_config(ctx):
    """The pi models.json dict with provider `coder` pointing at the remote server. The key itself is never
    in it: apiKey is the shell command that reads the key at runtime from key_path(), the configured key
    file or the 0600 temp file written when the key came from the env or Doppler."""
    return {
        "providers": {
            "coder": {
                "baseUrl": url(),
                "api": "openai-completions",
                "apiKey": "!cat " + shlex.quote(key_path()),
                # Qwen3-Coder has no thinking mode; ctx is the remote server's context window
                "models": [
                    {
                        "id": alias(),
                        "reasoning": False,
                        "contextWindow": ctx,
                        "maxTokens": MAX_TOKENS,
                    }
                ],
            }
        }
    }


def note(msg):
    """One stderr line, prefixed like coder_pi's own notes; callers pass no URL, host or key."""
    print("coder-30b: " + msg, file=sys.stderr)
