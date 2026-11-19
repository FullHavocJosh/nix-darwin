"""Tests for coder_pi.py (aidev's 30B builder). A stub llama-server, a stub pi and a fake remote server
thread stand in for the real ones: no model, everything on loopback. Run: PYTHONDONTWRITEBYTECODE=1
python3 .config/aistack/tests/test_coder_pi.py
"""

import fcntl
import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WRAPPER = os.path.join(os.path.dirname(HERE), "coder_pi.py")
FAILS = []

for k in (
    "AIDEV_REMOTE_BUILDER_URL",
    "AIDEV_REMOTE_BUILDER_KEY_FILE",
    "AIDEV_REMOTE_BUILDER_MODEL",
    "AIDEV_REMOTE_BUILDER_KEY",
):
    os.environ.pop(
        k, None
    )  # keep the local-path checks hermetic whatever the caller has set
# off: no default-gateway probe or Doppler call; an explicit URL below still wins
os.environ["AIDEV_REMOTE_BUILDER"] = "off"


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
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
json.dump({{'argv': sys.argv[1:], 'models': models, 'stdin': sys.stdin.read(), 'lock_held': held, 'dir': d,
           'entries': sorted(os.listdir(d)) if d and os.path.isdir(d) else []}}, open({REC!r}, 'w'))
if os.environ.get('STUB_SLEEP'):
    import time; time.sleep(float(os.environ['STUB_SLEEP']))
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
ENV = {
    **os.environ,
    "LOCAL_EDIT_MODEL_FILE": MODEL,
    "LOCAL_EDIT_PORT": str(PORT),
    "LOCAL_EDIT_STATE_DIR": STATE,
    "LLAMA_SERVER_BIN": BIN + "/llama-server",
    "LOCAL_EDIT_IDLE_S": "3",
    "CODER_PI_BIN": BIN + "/pi",
    "CODER_PI_AGENT_DIR": AGENT,
}


def run(args, env=None, stdin="build task T1"):
    return subprocess.run(
        [sys.executable, WRAPPER, *args],
        input=stdin,
        capture_output=True,
        text=True,
        env={**ENV, **(env or {})},
        timeout=60,
    )


def serving():
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=1).close()
        return True
    except OSError:
        return False


def watcher_alive():
    """True while an idle watcher holds STATE/watcher.lock; it releases the flock as it exits."""
    try:
        fd = os.open(STATE + "/watcher.lock", os.O_RDONLY)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return True
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    return False


print("pi on the 30B")
r = run(["--print", "--mode", "json", "--model", "coder/qwen3-coder-30b"])
rec = json.load(open(REC))
check(
    "pi runs with the caller's arguments",
    r.returncode == 0
    and rec["argv"][0] == "-e"
    and rec["argv"][1].endswith("worktree-guard.ts")
    and os.path.isfile(rec["argv"][1])
    and rec["argv"][2:]
    == ["--print", "--mode", "json", "--model", "coder/qwen3-coder-30b"],
    (r.returncode, r.stderr, rec),
)
check("the task prompt reaches pi on stdin", rec["stdin"] == "build task T1")
check(
    "pi's JSON output passes through to the caller", '"agent_end"' in r.stdout, r.stdout
)
prov = (rec["models"] or {}).get("providers", {}).get("coder", {})
check(
    "pi's agent dir points the coder provider at the 30B server",
    prov.get("baseUrl") == f"http://127.0.0.1:{PORT}/v1"
    and prov["models"][0]["id"] == "qwen3-coder-30b"
    and prov["models"][0]["reasoning"] is False,
    prov,
)
check(
    "the 30B lock is held while pi runs (one 30B job at a time)",
    rec["lock_held"] is True,
)
check(
    "pi's exit code is the wrapper's",
    run(["--print"], env={"STUB_RC": "7"}).returncode == 7,
)

print("hold mode (aider for aidev -p)")
r = run(["--hold", "--", BIN + "/pi", "--from-aider"])
rec = json.load(open(REC))
check(
    "--hold runs the given command with the lock held",
    r.returncode == 0 and rec["argv"] == ["--from-aider"] and rec["lock_held"],
    (r.stderr, rec),
)
check(
    "--hold without a command is a usage error", run(["--hold", "--"]).returncode == 2
)

print("unloading and availability")
t0 = time.time()
while (serving() or os.path.exists(STATE + "/server.pid")) and time.time() - t0 < 25:
    time.sleep(0.5)
check(
    "the idle watcher unloads the 30B after LOCAL_EDIT_IDLE_S",
    not serving() and not os.path.exists(STATE + "/server.pid"),
    round(time.time() - t0),
)
r = run(["--print"], env={"LOCAL_EDIT_MODEL_FILE": T + "/missing.gguf"})
check(
    "no 30B on this host: exit 3 so the driver moves on",
    r.returncode == 3 and "32 GB" in r.stderr,
    (r.returncode, r.stderr),
)

print("the remote builder (the G14)")
KEY = "sk-remote-coder-pi-4f2e"  # a sentinel that must never reach any stderr
KEY_FILE = T + "/remote.key"
open(KEY_FILE, "w").write(KEY + "\n")
t0 = time.time()  # wait out the last idle watcher (it exits once the server is gone), then clear its marker
while watcher_alive() and time.time() - t0 < 10:
    time.sleep(0.2)
os.remove(STATE + "/watcher.lock")
os.remove(AGENT + "/settings.json")  # the remote path must write it again


class Remote(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # the healthy G14: /v1/models lists the alias
        body = json.dumps({"data": [{"id": "qwen3-coder-30b"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


RPORT = free_port()
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", RPORT), Remote)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
RENV = {
    "AIDEV_REMOTE_BUILDER_URL": f"http://127.0.0.1:{RPORT}/v1",
    "AIDEV_REMOTE_BUILDER_KEY_FILE": KEY_FILE,
}

r = run(
    ["--print", "--mode", "json"],
    env={**RENV, "LOCAL_EDIT_MODEL_FILE": T + "/missing.gguf"},
)
rec = json.load(open(REC))
prov = (rec["models"] or {}).get("providers", {}).get("coder", {})
check(
    "a healthy remote: pi's coder provider points at it, no local model needed",
    r.returncode == 0
    and prov.get("baseUrl") == RENV["AIDEV_REMOTE_BUILDER_URL"]
    and prov["models"][0]["id"] == "qwen3-coder-30b"
    and prov["models"][0]["reasoning"] is False,
    (r.returncode, r.stderr, prov),
)
check(
    "a healthy remote: the key file, not the key, is written for pi",
    str(prov.get("apiKey", "")).startswith("!cat ")
    and KEY_FILE in prov["apiKey"]
    and KEY not in json.dumps(rec["models"]),
    prov.get("apiKey"),
)
check(
    "a healthy remote: the compaction settings write still happens",
    os.path.isfile(AGENT + "/settings.json")
    and json.load(open(AGENT + "/settings.json"))["compaction"]["enabled"] is False,
)
check(
    "a healthy remote: the local lock is not held while pi runs",
    rec["lock_held"] is False,
    rec,
)
check(
    "a healthy remote: no local server starts",
    not serving() and not os.path.exists(STATE + "/server.pid"),
    serving(),
)
check(
    "a healthy remote: nothing on stderr, no key or URL in it",
    "coder-30b" not in r.stderr and KEY not in r.stderr and str(RPORT) not in r.stderr,
    r.stderr,
)
time.sleep(0.5)  # a spawned watcher would have created its lock file by now
check(
    "a healthy remote: no idle watcher spawns",
    not os.path.exists(STATE + "/watcher.lock") and not watcher_alive(),
)

r = run(["--hold", "--", BIN + "/pi", "--from-aider-remote"], env=RENV)
rec = json.load(open(REC))
check(
    "hold mode with a healthy remote: the command runs as is, no local lock",
    r.returncode == 0
    and rec["argv"] == ["--from-aider-remote"]
    and rec["lock_held"] is False
    and "coder-30b" not in r.stderr
    and KEY not in r.stderr
    and str(RPORT) not in r.stderr,
    (r.returncode, r.stderr, rec),
)

CALLER = T + "/caller-agent"  # the pane's pi dir in hold mode
os.makedirs(CALLER)
open(CALLER + "/settings.json", "w").write('{"keep": true}')
open(CALLER + "/models.json", "w").write('{"providers": {}}')
r = run(
    ["--hold", "--", BIN + "/pi", "--from-aider-remote"],
    env={**RENV, "PI_CODING_AGENT_DIR": CALLER},
)
rec = json.load(open(REC))
prov = (rec["models"] or {}).get("providers", {}).get("coder", {})
check(
    "hold mode with a healthy remote: pi sees a private agent dir with the remote models.json",
    r.returncode == 0
    and rec["dir"] != CALLER
    and prov.get("baseUrl") == RENV["AIDEV_REMOTE_BUILDER_URL"]
    and "settings.json" in rec["entries"],
    (r.returncode, r.stderr, rec),
)
check(
    "hold mode with a healthy remote: the caller's dir is unchanged, the private one is removed",
    sorted(os.listdir(CALLER)) == ["models.json", "settings.json"]
    and open(CALLER + "/models.json").read() == '{"providers": {}}'
    and open(CALLER + "/settings.json").read() == '{"keep": true}'
    and not os.path.exists(rec["dir"]),
    os.listdir(CALLER),
)

# a remote that is healthy at first, then closes while pi runs
MPORT = free_port()
mid = http.server.ThreadingHTTPServer(("127.0.0.1", MPORT), Remote)
threading.Thread(target=mid.serve_forever, daemon=True).start()
if os.path.exists(REC):
    os.remove(REC)
t0 = time.monotonic()
p = subprocess.Popen(
    [sys.executable, WRAPPER, "--hold", "--", BIN + "/pi", "--from-aider-mid"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env={
        **ENV,
        "AIDEV_REMOTE_BUILDER_URL": f"http://127.0.0.1:{MPORT}/v1",
        "AIDEV_REMOTE_BUILDER_KEY_FILE": KEY_FILE,
        "AIDEV_REMOTE_BUILDER_MONITOR_S": "1",
        "STUB_SLEEP": "20",
    },
)
p.stdin.write("build task T3")
p.stdin.close()
while not os.path.exists(REC) and time.monotonic() - t0 < 10:
    time.sleep(0.1)
mid.shutdown()
mid.server_close()
try:
    err = p.stderr.read()
    rc = p.wait(timeout=15)
except subprocess.TimeoutExpired:
    p.kill()
    err, rc = "", None
dt = time.monotonic() - t0
check(
    "the remote dies mid-job: pi is stopped and the wrapper exits 3 within 15 s",
    rc == 3 and dt < 15,
    (rc, round(dt, 1)),
)
check(
    "the remote dies mid-job: one partial-edit line, no key or URL",
    err.count(
        "coder-30b: remote builder died mid-job; the work dir may hold a partial edit"
    )
    == 1
    and "git status" in err
    and KEY not in err
    and str(MPORT) not in err
    and "127.0.0.1" not in err,
    err,
)
r = run(["--hold", "--", BIN + "/pi", "--exits-by-itself"], env=RENV)
check(
    "a command that exits by itself returns its own code",
    r.returncode == 0 and "mid-job" not in r.stderr,
    (r.returncode, r.stderr),
)

t0 = (
    time.monotonic()
)  # env unset: the local path, and the timing baseline for the down-remote run
r = run(["--print"])
dt_local = time.monotonic() - t0
rec = json.load(open(REC))
check(
    "env unset: no probe output, the local path runs unchanged",
    "remote builder unavailable" not in r.stderr
    and (rec["models"] or {}).get("providers", {}).get("coder", {}).get("baseUrl")
    == f"http://127.0.0.1:{PORT}/v1"
    and rec["lock_held"] is True,
    (r.stderr, rec),
)

DOWN = free_port()  # nothing listens here: the probe is refused at once
t0 = time.monotonic()
r = run(
    ["--print"],
    env={
        "AIDEV_REMOTE_BUILDER_URL": f"http://127.0.0.1:{DOWN}/v1",
        "AIDEV_REMOTE_BUILDER_KEY_FILE": KEY_FILE,
    },
)
dt = time.monotonic() - t0
rec = json.load(open(REC))
check(
    "a down remote: one unavailable line, then the local path",
    r.returncode == 0
    and r.stderr.count(
        "coder-30b: remote builder unavailable (refused), using the local 30B"
    )
    == 1
    and (rec["models"] or {}).get("providers", {}).get("coder", {}).get("baseUrl")
    == f"http://127.0.0.1:{PORT}/v1"
    and rec["lock_held"] is True,
    (r.returncode, r.stderr, rec),
)
check(
    "the down-remote probe adds under 3 s",
    dt - dt_local < 3.0,
    f"{dt - dt_local:.2f} s over a {dt_local:.2f} s local run",
)
check(
    "no key text and no remote URL in any stderr",
    KEY not in r.stderr and str(RPORT) not in r.stderr and str(DOWN) not in r.stderr,
    r.stderr,
)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
