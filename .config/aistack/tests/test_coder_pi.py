"""Tests for coder_pi.py (aidev's 30B builder, RFC 0002). A stub llama-server and a stub pi stand in for the real
ones: no model, no network. Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_coder_pi.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WRAPPER = os.path.join(os.path.dirname(HERE), "coder_pi.py")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="coder-pi-"))
STATE, BIN, AGENT = T + "/state", T + "/bin", T + "/agent"
os.makedirs(BIN)
MODEL = T + "/model.gguf"
open(MODEL, "w").write("stub")
REC = T + "/pi.json"

open(BIN + "/llama-server", "w").write("""#!/usr/bin/env python3
import http.server, json, sys
a = sys.argv; port = int(a[a.index('--port') + 1]); alias = a[a.index('--alias') + 1]
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = json.dumps({"data": [{"id": alias}]}).encode(); self.send_response(200); self.end_headers(); self.wfile.write(b)
    def log_message(self, *x): pass
http.server.HTTPServer(('127.0.0.1', port), H).serve_forever()
""")
# stub pi: records argv, its agent dir's models.json, stdin, and whether the 30B lock is held while it runs
open(BIN + "/pi", "w").write(f"""#!/usr/bin/env python3
import fcntl, json, os, sys
d = os.environ.get('PI_CODING_AGENT_DIR', '')
models = json.load(open(d + '/models.json')) if d and os.path.exists(d + '/models.json') else None
with open({STATE!r} + '/edit.lock', 'a') as lf:
    try:
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB); held = False
    except OSError:
        held = True
json.dump({{'argv': sys.argv[1:], 'models': models, 'stdin': sys.stdin.read(), 'lock_held': held}}, open({REC!r}, 'w'))
print(json.dumps({{'type': 'agent_end'}}))
sys.exit(int(os.environ.get('STUB_RC', '0')))
""")
for f in ("llama-server", "pi"):
    os.chmod(f"{BIN}/{f}", 0o755)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = free_port()
ENV = {**os.environ, "LOCAL_EDIT_MODEL_FILE": MODEL, "LOCAL_EDIT_PORT": str(PORT), "LOCAL_EDIT_STATE_DIR": STATE,
       "LLAMA_SERVER_BIN": BIN + "/llama-server", "LOCAL_EDIT_IDLE_S": "3", "CODER_PI_BIN": BIN + "/pi",
       "CODER_PI_AGENT_DIR": AGENT}


def run(args, env=None, stdin="build task T1"):
    return subprocess.run([sys.executable, WRAPPER, *args], input=stdin, capture_output=True, text=True,
                          env={**ENV, **(env or {})}, timeout=60)


def serving():
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=1).close()
        return True
    except OSError:
        return False


print("pi on the 30B")
r = run(["--print", "--mode", "json", "--model", "coder/qwen3-coder-30b"])
rec = json.load(open(REC))
check("pi runs with Ralph's arguments", r.returncode == 0 and rec["argv"] == ["--print", "--mode", "json", "--model", "coder/qwen3-coder-30b"], (r.returncode, r.stderr, rec))
check("the task prompt reaches pi on stdin", rec["stdin"] == "build task T1")
check("pi's JSON output passes through to Ralph", '"agent_end"' in r.stdout, r.stdout)
prov = (rec["models"] or {}).get("providers", {}).get("coder", {})
check("pi's agent dir points the coder provider at the 30B server", prov.get("baseUrl") == f"http://127.0.0.1:{PORT}/v1"
      and prov["models"][0]["id"] == "qwen3-coder-30b" and prov["models"][0]["reasoning"] is False, prov)
check("the 30B lock is held while pi runs (one 30B job at a time)", rec["lock_held"] is True)
check("pi's exit code is the wrapper's", run(["--print"], env={"STUB_RC": "7"}).returncode == 7)

print("hold mode (aider for aidev -p)")
r = run(["--hold", "--", BIN + "/pi", "--from-aider"])
rec = json.load(open(REC))
check("--hold runs the given command with the lock held", r.returncode == 0 and rec["argv"] == ["--from-aider"] and rec["lock_held"], (r.stderr, rec))
check("--hold without a command is a usage error", run(["--hold", "--"]).returncode == 2)

print("unloading and availability")
t0 = time.time()
while (serving() or os.path.exists(STATE + "/server.pid")) and time.time() - t0 < 25:
    time.sleep(0.5)
check("the idle watcher unloads the 30B after LOCAL_EDIT_IDLE_S", not serving() and not os.path.exists(STATE + "/server.pid"), round(time.time() - t0))
r = run(["--print"], env={"LOCAL_EDIT_MODEL_FILE": T + "/missing.gguf"})
check("no 30B on this host: exit 3 so the driver moves on", r.returncode == 3 and "32 GB" in r.stderr, (r.returncode, r.stderr))

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
