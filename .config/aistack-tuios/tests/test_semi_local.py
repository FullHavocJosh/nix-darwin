"""Tests for aidev's semi-local builder (aidev_tuios.py semi_local_available, auto_builder, build_body, next_tier): the
authenticated GET of the gateway /models gates it, the bearer key is read at runtime and never written. Needs no tuios daemon, no
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
    """A 127.0.0.1 server: GET /models answers `status` with the alias list when the bearer key is test-key, else 401;
    status "hang" holds the request for 2 s; returns (server, port)."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/v1/models":
                code, body = 404, b""
            elif self.headers.get("Authorization") != "Bearer test-key":
                code, body = 401, b""
            elif status[0] == "hang":
                time.sleep(2)
                code, body = 200, b""
            else:
                code, body = status[0], json.dumps({"data": [{"id": "qwen3-coder-30b"}]}).encode()
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def main():
    for var in ("AIDEV_TUIOS_SESSION", "AIDEV_TUIOS_RUN", "AIDEV_TUIOS_PROJECT", "AIDEV_TUIOS_BUILDER",
                "AIDEV_SEMI_LOCAL", "AIDEV_SEMI_LOCAL_URL", "AIDEV_REMOTE_BUILDER_KEY_FILE"):
        os.environ.pop(var, None)
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_HOME"] = tmp
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    secret = "test-key"
    key_file = os.path.join(tmp, "api-key")
    with open(os.open(key_file, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
        f.write(secret)
    status = [200]
    srv, port = serve(status)
    a.SEMI_URL = f"http://127.0.0.1:{port}/v1"
    a.SEMI_KEY_FILE = key_file

    print("semi_local_available")
    check("online: /models 200 with the alias", a.semi_local_available() is True)
    status[0] = 503
    check("503: unavailable", a.semi_local_available() is False)
    status[0] = 200
    a.SEMI_KEY_FILE = os.path.join(tmp, "wrong-key")
    with open(os.open(a.SEMI_KEY_FILE, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
        f.write("wrong")
    check("401 (wrong key): unavailable", a.semi_local_available() is False)
    a.SEMI_KEY_FILE = key_file

    real_timeout = a.SEMI_TIMEOUT_S
    status[0] = "hang"
    a.SEMI_TIMEOUT_S = 0.5
    t0 = time.time()
    ok = a.semi_local_available()
    check("timeout: unavailable within 3 s", ok is False and time.time() - t0 < 3, time.time() - t0)
    a.SEMI_TIMEOUT_S = real_timeout
    status[0] = 200

    real_lrb, real_ai_home = a.load_remote_builder, os.environ.get("AI_HOME")

    class NoKey:
        @staticmethod
        def read_key():
            return None

    ai_home = os.path.join(tmp, "ai-home")
    try:
        a.SEMI_KEY_FILE = ""
        a.load_remote_builder = lambda: NoKey
        os.environ["AI_HOME"] = ai_home
        check("no key anywhere: unavailable", a.semi_local_available() is False)
    finally:
        a.SEMI_KEY_FILE = key_file
        a.load_remote_builder = real_lrb
        if real_ai_home is None:
            os.environ.pop("AI_HOME", None)
        else:
            os.environ["AI_HOME"] = real_ai_home

    class Done:
        def __init__(self, returncode, stdout):
            self.returncode, self.stdout = returncode, stdout

    def stub(result, calls):
        def run(cmd, *args, **kwargs):
            calls.append((cmd, kwargs))
            if isinstance(result, BaseException):
                raise result
            return result
        return run

    real_run = a.subprocess.run
    try:
        calls = []
        a.subprocess.run = stub(Done(0, '{"data":[{"id":"qwen3-coder-30b"}]}\n200'), calls)
        check("mock curl 200: available", a.semi_local_available() is True)
        cmd, kwargs = calls[0]
        check("probe is /usr/bin/curl ... /models, no shell",
              isinstance(cmd, list) and cmd[0] == "/usr/bin/curl" and cmd[-1] == f"http://127.0.0.1:{port}/v1/models"
              and not kwargs.get("shell"), calls[0])
        check("curl argv holds no key", not any(secret in str(part) for part in cmd), cmd)
        check("curl stdin holds the bearer header", "Authorization: Bearer test-key" in (kwargs.get("input") or ""),
              kwargs.get("input"))
        for name, result in (("curl exit 7", Done(7, "")), ("curl 503", Done(0, "\n503")),
                             ("curl timeout", a.subprocess.TimeoutExpired("curl", 1)),
                             ("curl OSError 65", OSError(65, "No route to host"))):
            a.subprocess.run = stub(result, [])
            check(name + ": unavailable", a.semi_local_available() is False)
        calls = []
        a.subprocess.run = stub(Done(0, '{"data":[{"id":"qwen3-coder-30b"}]}\n200'), calls)
        os.environ["AIDEV_SEMI_LOCAL"] = "off"
        check("kill switch: unavailable, curl not run", a.semi_local_available() is False and not calls)
        os.environ.pop("AIDEV_SEMI_LOCAL")
    finally:
        a.subprocess.run = real_run
        os.environ.pop("AIDEV_SEMI_LOCAL", None)

    print("semi_key_file cache")
    class AbcKey:
        @staticmethod
        def read_key():
            return "abc"

    ai_home = os.path.join(tmp, "ai-home-cache")
    try:
        a.SEMI_KEY_FILE = ""
        a.load_remote_builder = lambda: AbcKey
        os.environ["AI_HOME"] = ai_home
        path = a.semi_key_file()
        expect = os.path.join(ai_home, "cache", "aidev_tuios", "semi-key")
        check("cache file path is <AI_HOME>/cache/aidev_tuios/semi-key", path == expect, path)
        check("cache file mode is 0600", os.stat(expect).st_mode & 0o777 == 0o600)
        with open(expect) as f:
            check("cache file holds the key", f.read() == "abc")
    except OSError as e:
        check("cache file written", False, e)
    finally:
        a.SEMI_KEY_FILE = key_file
        a.load_remote_builder = real_lrb
        if real_ai_home is None:
            os.environ.pop("AI_HOME", None)
        else:
            os.environ["AI_HOME"] = real_ai_home

    print("auto_builder")
    real = (a.semi_local_available, a.local_builder_available, a.zen_status, a.zen_usable)
    try:
        a.zen_status = lambda run, refresh=False: {"state": "available", "model": "m", "detail": ""}
        a.zen_usable = lambda s: True
        a.semi_local_available, a.local_builder_available = (lambda: True), (lambda: True)
        check("semi up: semi-local", a.auto_builder(None) == "tier-2")
        a.semi_local_available = lambda: False
        check("semi down, local up: local", a.auto_builder(None) == "tier-0")
        a.local_builder_available = lambda: False
        check("both down, zen usable: free", a.auto_builder(None) == "tier-3")
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
        check("semi down: build_body is None", a.build_body(run, cfg, "tier-2") is None)
        status[0] = 200
        body = a.build_body(run, cfg, "tier-2")
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
    check("semi body runs pi without the coder wrapper",
          isinstance(body, str) and "coder_pi" not in body and "pi --model semi/qwen3-coder-30b" in body, body)
    real_lba = a.local_builder_available
    a.write_git_guard = lambda r: a.write_text(os.path.join(r.dir, "bin", "guard", "git"), "")
    a.local_builder_available = lambda: True
    try:
        local_body = a.build_body(run, cfg, "tier-0")
    finally:
        a.write_git_guard, a.local_builder_available = real_gg, real_lba
    check("local body still uses the coder wrapper", isinstance(local_body, str) and "coder_pi" in local_body, local_body)

    print("write_build_pi")
    pi_cfg = {"pi_build": os.path.join(tmp, "pi-build-gw")}
    a.write_build_pi(pi_cfg, "tier-2")
    with open(os.path.join(pi_cfg["pi_build"], "models.json")) as f:
        gw_text = f.read()
    gw = json.loads(gw_text).get("providers", {}).get("semi", {})
    check("models.json semi.baseUrl is SEMI_URL", gw.get("baseUrl") == a.SEMI_URL, gw)
    check("models.json semi.apiKey is a '!cat ' command", str(gw.get("apiKey", "")).startswith("!cat "), gw)
    check("models.json does not contain the key", secret not in gw_text)

    print("next_tier")
    check("tier-2 then tier-3 (local off)", a.next_tier("tier-2", "available", False) == "tier-3")
    check("semi-local without local then free", a.next_tier("tier-2", "available", local_ok=False) == "tier-3")

    srv.shutdown()
    print()
    print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
