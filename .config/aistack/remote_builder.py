#!/usr/bin/env python3
"""aidev's remote builder: the 30B coder model served by an OpenAI-compatible llama-server on another
machine (the G14), so the local one need not be loaded.

With AIDEV_REMOTE_BUILDER_URL (an OpenAI base such as http://HOST:8082/v1) and AIDEV_REMOTE_BUILDER_KEY_FILE
set, probe() checks in under timeout + 0.5 s that the server answers /models with the model alias
(qwen3-coder-30b, or AIDEV_REMOTE_BUILDER_MODEL); models_config(ctx) is then the pi models.json dict that
points provider `coder` at it. The key itself never appears in anything this module returns or writes:
models.json carries apiKey "!cat <key file>", so pi reads the key at runtime from the file. Failure reasons
are short fixed words ("timeout", "refused", "http 401") that never contain the URL, host or key, because
the driver prints them with note() as it falls through to the local 30B, then Zen.

The remote path skips the local edit.lock and the 2-minute idle unload: that machine owns its model. With
the env unset configured() is False and nothing changes. Stdlib only.
"""

import json
import os
import shlex
import sys
import urllib.error
import urllib.request

URL_ENV = "AIDEV_REMOTE_BUILDER_URL"  # an OpenAI base, such as http://HOST:8082/v1
KEY_FILE_ENV = (
    "AIDEV_REMOTE_BUILDER_KEY_FILE"  # the file the server's bearer key lives in
)
MODEL_ENV = "AIDEV_REMOTE_BUILDER_MODEL"  # overrides DEFAULT_ALIAS
DEFAULT_ALIAS = "qwen3-coder-30b"
PROBE_TIMEOUT_S = 2.0
MAX_TOKENS = 8192


def url():
    """The configured OpenAI base without a trailing slash; '' when unset."""
    return os.environ.get(URL_ENV, "").strip().rstrip("/")


def key_file():
    """The configured key file path; '' when unset."""
    return os.environ.get(KEY_FILE_ENV, "").strip()


def alias():
    """The remote model's id: AIDEV_REMOTE_BUILDER_MODEL, or the default qwen3-coder-30b."""
    return os.environ.get(MODEL_ENV, "").strip() or DEFAULT_ALIAS


def configured():
    """True only when both the remote builder URL and its key file are set to something."""
    return bool(url() and key_file())


def read_key():
    """The stripped contents of the key file, or None when it cannot be read."""
    try:
        with open(key_file()) as fh:
            return fh.read().strip()
    except OSError:
        return None


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
        return False, "no key file"
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


def models_config(ctx):
    """The pi models.json dict with provider `coder` pointing at the remote server. The key itself is never
    in it: apiKey is the shell command that reads the key file at runtime."""
    return {
        "providers": {
            "coder": {
                "baseUrl": url(),
                "api": "openai-completions",
                "apiKey": "!cat " + shlex.quote(key_file()),
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
