"""Tests for remote_builder.py (the 30B coder model on a remote OpenAI-compatible server). A fake
llama-server stands in for the real one on 127.0.0.1: healthy (asserts the bearer key), wrong-key (401),
slow (sleeps 5 s, past the probe timeout) and down (a closed port). No model, no real network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_remote_builder.py
"""

import contextlib
import http.server
import io
import json
import os
import shlex
import socket
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import remote_builder as rb

FAILS = []
KEY = "sk-remote-builder-test-key"
SEEN = {}

for k in (rb.URL_ENV, rb.KEY_FILE_ENV, rb.MODEL_ENV, rb.KEY_ENV):
    os.environ.pop(k, None)  # keep this run hermetic whatever the caller has set
os.environ[rb.OFF_ENV] = "off"  # the new defaults off too, for the same reason


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def make_handler(mode):
    """healthy: the alias behind the bearer key (401 without it). wrong-key: 401 whatever is sent.
    slow: sleeps 5 s, longer than the probe timeout."""

    class H(http.server.BaseHTTPRequestHandler):
        def reply(self, code, obj):
            body = json.dumps(obj).encode()
            try:
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                pass  # the probe timed out and closed the socket before we answered

        def do_GET(self):
            SEEN["auth"] = self.headers.get("Authorization", "")
            if mode == "slow":
                time.sleep(5)
            if mode == "healthy" and SEEN["auth"] == "Bearer " + KEY:
                self.reply(200, {"data": [{"id": "qwen3-coder-30b"}]})
            else:
                self.reply(401, {"error": {"message": "invalid key"}})

        def log_message(self, *args):
            pass

    return H


def start_server(mode):
    """The fake server on a fresh loopback port, in a daemon thread; returns (port, httpd)."""
    port = free_port()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), make_handler(mode))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return port, httpd


def stop_server(httpd):
    httpd.shutdown()
    httpd.server_close()


print("environment")
check("configured() is False with the env unset", rb.configured() is False)
ok, reason = rb.probe()
check(
    "probe with the env unset fails safely",
    ok is False and isinstance(reason, str) and KEY not in reason,
    (ok, reason),
)
KEY_FILE = os.path.join(tempfile.mkdtemp(prefix="remote-builder-"), "key")
open(KEY_FILE, "w").write(KEY + "\n")
os.environ[rb.KEY_FILE_ENV] = KEY_FILE
check("configured() is False with only the key file set", rb.configured() is False)
check("read_key() returns the stripped key", rb.read_key() == KEY, rb.read_key())
os.environ[rb.KEY_FILE_ENV] = KEY_FILE + "-missing"
check("read_key() is None for a missing file", rb.read_key() is None)
os.environ[rb.KEY_FILE_ENV] = KEY_FILE
os.environ[rb.URL_ENV] = "http://127.0.0.1:1/v1"
check("configured() is True with URL and key file set", rb.configured() is True)

print("probe")
PORT, HTTPD = start_server("healthy")
os.environ[rb.URL_ENV] = f"http://127.0.0.1:{PORT}/v1"
t0 = time.monotonic()
ok, reason = rb.probe()
check("probe ok on a healthy server", ok is True, reason)
check("the healthy probe is quick", time.monotonic() - t0 < 3.0)
check(
    "probe sent the bearer key from the key file",
    SEEN.get("auth") == "Bearer " + KEY,
    SEEN,
)
stop_server(HTTPD)

PORT, HTTPD = start_server("wrong-key")
os.environ[rb.URL_ENV] = f"http://127.0.0.1:{PORT}/v1"
ok, reason = rb.probe()
check(
    "probe fails with 'http 401' on a wrong key",
    ok is False and reason == "http 401",
    (ok, reason),
)
check(
    "the 401 reason contains neither the port nor the key",
    str(PORT) not in reason and KEY not in reason,
    reason,
)
stop_server(HTTPD)

DOWN_PORT = free_port()  # nothing listens here
os.environ[rb.URL_ENV] = f"http://127.0.0.1:{DOWN_PORT}/v1"
ok, reason = rb.probe()
check("probe fails on a closed port", ok is False and reason == "refused", (ok, reason))
check(
    "the refused reason contains neither the port nor the key",
    str(DOWN_PORT) not in reason and KEY not in reason,
    reason,
)

PORT, HTTPD = start_server("slow")
os.environ[rb.URL_ENV] = f"http://127.0.0.1:{PORT}/v1"
t0 = time.monotonic()
ok, reason = rb.probe()
dt = time.monotonic() - t0
check(
    "probe gives up with 'timeout' on a server that sleeps 5 s",
    ok is False and reason == "timeout",
    (ok, reason),
)
check("the slow probe returns in under 3.0 s of wall time", dt < 3.0, f"{dt:.2f} s")
check(
    "the timeout reason contains neither the port nor the key",
    str(PORT) not in reason and KEY not in reason,
    reason,
)
stop_server(HTTPD)

print("models.json")
os.environ[rb.URL_ENV] = f"http://127.0.0.1:{PORT}/v1/"  # trailing slash on purpose
os.environ.pop(rb.MODEL_ENV, None)
mc = rb.models_config(32768)
text = json.dumps(mc)
coder = mc["providers"]["coder"]
check(
    "one coder provider in the pi models.json shape",
    set(mc) == {"providers"} and set(mc["providers"]) == {"coder"},
    text,
)
check(
    "baseUrl is the URL without its trailing slash",
    coder["baseUrl"] == f"http://127.0.0.1:{PORT}/v1",
    coder["baseUrl"],
)
check(
    "apiKey starts with '!cat ' and quotes the key file",
    coder["apiKey"].startswith("!cat ")
    and coder["apiKey"] == "!cat " + shlex.quote(KEY_FILE),
    coder["apiKey"],
)
check("the key text appears nowhere in models_config", KEY not in text, text)
check(
    "the model entry is the default alias with the ctx and 8192 max tokens",
    coder["models"]
    == [
        {
            "id": "qwen3-coder-30b",
            "reasoning": False,
            "contextWindow": 32768,
            "maxTokens": 8192,
        }
    ],
    coder["models"],
)
os.environ[rb.MODEL_ENV] = "other-coder-model"
check(
    "AIDEV_REMOTE_BUILDER_MODEL overrides the alias",
    rb.models_config(16384)["providers"]["coder"]["models"][0]["id"]
    == "other-coder-model",
)
os.environ.pop(rb.MODEL_ENV, None)

print("note")
err = io.StringIO()
with contextlib.redirect_stderr(err):
    rb.note("falling through to the local 30B")
check(
    "note prints one 'coder-30b: ' line to stderr",
    err.getvalue() == "coder-30b: falling through to the local 30B\n",
    err.getvalue(),
)

print("defaults and the off switch")
saved_env = dict(os.environ)  # each block below restores the whole env, PATH included
os.environ.pop(rb.OFF_ENV, None)
os.environ.pop(rb.URL_ENV, None)
check(
    "url() is the default URL and configured() is True with nothing set",
    rb.url() == rb.DEFAULT_URL and rb.configured() is True,
    rb.url(),
)
os.environ[rb.OFF_ENV] = "off"
check(
    "configured() is False with the off switch set and no URL", rb.configured() is False
)
os.environ[rb.URL_ENV] = "http://127.0.0.1:1/v1"
check(
    "configured() is True with the off switch set and an explicit URL",
    rb.configured() is True and rb.url() == "http://127.0.0.1:1/v1",
    rb.url(),
)
os.environ.clear()
os.environ.update(saved_env)

print("key from the env")
saved_env = dict(os.environ)
os.environ.pop(rb.KEY_FILE_ENV, None)
os.environ[rb.KEY_ENV] = "  sk-env-key \n"
check(
    "read_key() returns the stripped KEY_ENV value when no key file is set",
    rb.read_key() == "sk-env-key",
    rb.read_key(),
)
os.environ.clear()
os.environ.update(saved_env)

print("doppler")
DOP_KEY = "sk-from-doppler"
DOPPLER_DIR = tempfile.mkdtemp(prefix="remote-builder-doppler-")
STUB = os.path.join(DOPPLER_DIR, "doppler")


def write_stub(src):
    """The fake doppler CLI: prints the key, or fails; 0755 so PATH lookup runs it."""
    with open(STUB, "w") as fh:
        fh.write(src)
    os.chmod(STUB, 0o755)


saved_env = dict(os.environ)
os.environ["PATH"] = DOPPLER_DIR + os.pathsep + os.environ["PATH"]
os.environ.pop(rb.KEY_FILE_ENV, None)
os.environ.pop(rb.KEY_ENV, None)
write_stub(f"#!/bin/sh\necho {DOP_KEY}\n")
rb.reset_key_cache()
check(
    "read_key() returns the key the doppler stub prints",
    rb.read_key() == DOP_KEY,
    rb.read_key(),
)
os.unlink(STUB)  # the cache must answer without the CLI
check(
    "read_key() is unchanged after the doppler stub is deleted (the cache)",
    rb.read_key() == DOP_KEY,
    rb.read_key(),
)
write_stub("#!/bin/sh\nexit 1\n")
rb.reset_key_cache()
check("read_key() is None when doppler exits 1", rb.read_key() is None, rb.read_key())
os.environ[rb.URL_ENV] = "http://127.0.0.1:1/v1"
ok, reason = rb.probe()
check(
    "probe fails with 'no key' when doppler fails",
    (ok, reason) == (False, "no key"),
    (ok, reason),
)
os.environ.clear()
os.environ.update(saved_env)

print("key_path")
saved_env = dict(os.environ)
os.environ[rb.KEY_FILE_ENV] = KEY_FILE
check(
    "key_path() is the configured key file when one is set",
    rb.key_path() == KEY_FILE,
    rb.key_path(),
)
os.environ.pop(rb.KEY_FILE_ENV, None)
os.environ.pop(rb.KEY_ENV, None)
os.environ["PATH"] = DOPPLER_DIR + os.pathsep + os.environ["PATH"]
write_stub(f"#!/bin/sh\necho {DOP_KEY}\n")
rb.reset_key_cache()
tmp_key = rb.key_path()
st = os.stat(tmp_key) if tmp_key else None
check(
    "key_path() with the doppler key is a 0600 file holding the key",
    st is not None
    and (st.st_mode & 0o777) == 0o600
    and open(tmp_key).read().strip() == DOP_KEY,
    (tmp_key, oct(st.st_mode & 0o777) if st else None),
)
api_key = rb.models_config(32768)["providers"]["coder"]["apiKey"]
check(
    "apiKey cats the doppler temp key file, never the key itself",
    api_key.startswith("!cat ") and tmp_key in api_key and DOP_KEY not in api_key,
    api_key,
)
# per-device key: the default key file wins over Doppler; Doppler tries LLM_KEY_<DEVICE> first
os.environ.pop(rb.KEY_FILE_ENV, None)
os.environ.pop(rb.KEY_ENV, None)
dev_dir = tempfile.mkdtemp()
rb.DEVICE_KEY_FILE = os.path.join(dev_dir, "key")
with open(rb.DEVICE_KEY_FILE, "w") as fh:
    fh.write("devfilekey\n")
rb.reset_key_cache()
check("read_key() uses the device key file before Doppler", rb.read_key() == "devfilekey", None)
os.unlink(rb.DEVICE_KEY_FILE)
os.environ["AISTACK_GATEWAY_KEY"] = " shared-env-key \n"
rb.reset_key_cache()
check("read_key() accepts AISTACK_GATEWAY_KEY, stripped", rb.read_key() == "shared-env-key", None)
os.environ.pop("AISTACK_GATEWAY_KEY", None)
write_stub('#!/bin/sh\necho "key-$3"\n')
os.environ[rb.DEVICE_ENV] = "macbook-m2pro"
rb.reset_key_cache()
check("doppler_key() asks LLM_KEY_<DEVICE> first", rb.read_key() == "key-LLM_KEY_MACBOOK_M2PRO", None)
os.environ.pop(rb.DEVICE_ENV, None)
rb.reset_key_cache()
check("doppler_key() falls back to LLM_PUBLIC_API_KEY", rb.read_key() == "key-LLM_PUBLIC_API_KEY", None)
rb.reset_key_cache()
rb.TIERS_URL = "http://127.0.0.1:9/auto/v1/tiers"
check("gateway_health() is None when the gateway is unreachable", rb.gateway_health(0.5) is None, None)
os.environ.clear()
os.environ.update(saved_env)

print("\nFAILED:%s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
