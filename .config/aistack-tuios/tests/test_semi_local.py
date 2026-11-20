"""Tests for aidev's semi-local builder (aidev_tuios.py semi_local_available, auto_builder, build_body, next_tier): the
G14 llama server /health gates it, the bearer key is read at runtime and never written. Needs no tuios daemon, no
model and no network beyond 127.0.0.1.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_semi_local.py
"""
import http.server
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time

os.environ["AISTACK_ZEN_KEY"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(os.path.dirname(ROOT), "aistack")  # this checkout's zen_models.py
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def serve(status):
    """A 127.0.0.1 server answering `status` on /health; returns (server, port)."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status[0] if self.path == "/health" else 404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def main():
    for var in ("AIDEV_TUIOS_SESSION", "AIDEV_TUIOS_RUN", "AIDEV_TUIOS_PROJECT", "AIDEV_TUIOS_BUILDER",
                "AIDEV_SEMI_LOCAL"):
        os.environ.pop(var, None)
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_HOME"] = tmp
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    secret = "not-a-real-key-marker"
    key_file = os.path.join(tmp, "api-key")
    with open(os.open(key_file, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
        f.write(secret)
    status = [200]
    srv, port = serve(status)
    a.SEMI_URL = f"http://127.0.0.1:{port}/v1"
    a.SEMI_KEY_FILE = key_file

    print("semi_local_available")
    check("online: /health 200", a.semi_local_available() is True)
    status[0] = 503
    check("503: unavailable", a.semi_local_available() is False)
    status[0] = 200

    real_timeout = a.SEMI_TIMEOUT_S
    srv.shutdown()
    srv.server_close()
    a.SEMI_TIMEOUT_S = 0.5
    t0 = time.time()
    ok = a.semi_local_available()
    check("closed port: unavailable within 3 s", ok is False and time.time() - t0 < 3, time.time() - t0)
    a.SEMI_TIMEOUT_S = real_timeout

    srv, port = serve(status)
    a.SEMI_URL = f"http://127.0.0.1:{port}/v1"
    a.SEMI_KEY_FILE = os.path.join(tmp, "no-such-key")
    check("missing key file: unavailable", a.semi_local_available() is False)
    a.SEMI_KEY_FILE = key_file
    check("key file back: available", a.semi_local_available() is True)
    os.environ["AIDEV_SEMI_LOCAL"] = "off"
    check("AIDEV_SEMI_LOCAL=off: unavailable", a.semi_local_available() is False)
    os.environ.pop("AIDEV_SEMI_LOCAL")

    print("auto_builder")
    real = (a.semi_local_available, a.local_builder_available, a.zen_status, a.zen_usable)
    try:
        a.zen_status = lambda run, refresh=False: {"state": "available", "model": "m", "detail": ""}
        a.zen_usable = lambda s: True
        a.semi_local_available, a.local_builder_available = (lambda: True), (lambda: True)
        check("semi up: semi-local", a.auto_builder(None) == "semi-local")
        a.semi_local_available = lambda: False
        check("semi down, local up: local", a.auto_builder(None) == "local")
        a.local_builder_available = lambda: False
        check("both down, zen usable: free", a.auto_builder(None) == "free")
    finally:
        a.semi_local_available, a.local_builder_available, a.zen_status, a.zen_usable = real

    print("build_body")
    p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))
    run = a.Run(p, "semi-test")
    run.data.update(phase="build", work_dir=p)
    cfg = {"pi_build": os.path.join(tmp, "pi-build")}
    real_gg = a.write_git_guard
    a.write_git_guard = lambda r: a.write_text(os.path.join(r.dir, "bin", "guard", "git"), "")
    try:
        status[0] = 503
        check("semi down: build_body is None", a.build_body(run, cfg, "semi-local") is None)
        status[0] = 200
        body = a.build_body(run, cfg, "semi-local")
    finally:
        a.write_git_guard = real_gg
    check("semi up: body names the semi model", isinstance(body, str) and "semi/qwen3-coder-30b" in body, body)
    models_path = os.path.join(cfg["pi_build"], "models.json")
    with open(models_path) as f:
        models_text = f.read()
    semi = json.loads(models_text).get("providers", {}).get("semi", {})
    check("models.json has the semi provider", bool(semi), models_text[:300])
    check("semi apiKey reads the key file at runtime", str(semi.get("apiKey", "")).startswith("!cat "), semi)
    check("key contents are not in the body", secret not in (body or ""))
    check("key contents are not in models.json", secret not in models_text)

    print("next_tier")
    check("semi-local then local", a.next_tier("semi-local", "available") == "local")
    check("semi-local without local then free", a.next_tier("semi-local", "available", local_ok=False) == "free")

    srv.shutdown()
    print()
    print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
