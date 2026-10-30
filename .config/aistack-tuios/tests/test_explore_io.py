"""Test explore.py IO primitives: ctx_tokens, ask and read_files."""

import http.server
import importlib.util
import json
import os
import socket
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "explore", os.path.join(HERE, "..", "explore.py")
)
explore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(explore)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send({"default_generation_settings": {"n_ctx": 65536}})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self._send({"choices": [{"message": {"content": " hi "}}]})

    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
explore.BASE = f"http://127.0.0.1:{server.server_address[1]}"
check("ctx_tokens", explore.ctx_tokens() == 65536)
check("ask strips reply", explore.ask("x") == "hi")
server.shutdown()
server.server_close()

s = socket.socket()
s.bind(("127.0.0.1", 0))
explore.BASE = f"http://127.0.0.1:{s.getsockname()[1]}"
s.close()
check("ctx_tokens closed port is 0", explore.ctx_tokens() == 0)
try:
    explore.ask("x")
    check("ask closed port raises", False)
except RuntimeError:
    check("ask closed port raises", True)

with tempfile.TemporaryDirectory() as d:
    with open(os.path.join(d, "a.txt"), "w") as f:
        f.write("one\ntwo\n")
    text, skipped = explore.read_files(d, ["a.txt"], 1000)
    check("numbered text", text == "=== a.txt ===\n1: one\n2: two", repr(text))
    check("no skips", skipped == [], str(skipped))
    text, skipped = explore.read_files(d, ["../x"], 1000)
    check("outside root", skipped == ["../x: outside root"], str(skipped))
    text, skipped = explore.read_files(d, ["a.txt"], 5)
    check("over budget", skipped == ["a.txt: over budget"] and text == "", str(skipped))
    text, skipped = explore.read_files(d, ["nope"], 1000)
    check("missing", skipped == ["nope: missing"], str(skipped))
    with open(os.path.join(d, "b.bin"), "wb") as f:
        f.write(b"ab\0cd")
    text, skipped = explore.read_files(d, ["b.bin"], 1000)
    check("binary", skipped == ["b.bin: binary"], str(skipped))

sys.exit(1 if FAILS else 0)
