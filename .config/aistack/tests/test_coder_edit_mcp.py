"""Tests for local_edit_mcp.py (edits on the on-device coder model). A stub llama-server and a stub aider stand in for
the real ones: no model, no network. Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_coder_edit_mcp.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(os.path.dirname(HERE), "local_edit_mcp.py")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="local-edit-"))
REPO, STATE, BIN = T + "/repo", T + "/state", T + "/bin"
os.makedirs(REPO + "/src")
os.makedirs(BIN)
open(REPO + "/src/a.py", "w").write("def old_name():\n    return 1\n")
open(REPO + "/src/b.py", "w").write("from a import old_name\nprint(old_name())\n")
MAIN = T + "/main"
os.rename(REPO, MAIN)
subprocess.run(f"cd {MAIN} && git init -q && git add . && git -c user.name=t -c user.email=t@t commit -qm init"
               f" && git worktree add -q -b work {REPO}", shell=True)  # edits are allowed in a linked worktree only
MODEL = T + "/model.gguf"
open(MODEL, "w").write("stub")

# stub llama-server: serves /v1/models with the --alias it was given, after a short "load"
open(BIN + "/llama-server", "w").write("""#!/usr/bin/env python3
import http.server, sys, time
a = sys.argv; port = int(a[a.index('--port') + 1]); alias = a[a.index('--alias') + 1]
time.sleep(0.5)
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = ('{"data":[{"id":"%s"}]}' % alias).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(b)
    def log_message(self, *x): pass
http.server.HTTPServer(('127.0.0.1', port), H).serve_forever()
""")
# stub aider: "RENAME x y" renames in every file it was given; "NOTHING" changes nothing; records its argv
open(BIN + "/aider", "w").write("""#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
open(os.environ['STUB_LOG'], 'a').write(json.dumps(a) + '\\n')
msg = a[a.index('--message') + 1]; files = a[a.index('--message') + 2:]
if msg.startswith('RENAME'):
    _, old, new = msg.split()[:3]
    for f in files:
        t = open(f).read() if os.path.exists(f) else ''
        open(f, 'w').write(t.replace(old, new))
print('Applied edit')
""")
for f in ("llama-server", "aider"):
    os.chmod(BIN + "/" + f, 0o755)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = free_port()
ENV = {**os.environ, "LOCAL_EDIT_MODEL_FILE": MODEL, "LOCAL_EDIT_PORT": str(PORT), "LOCAL_EDIT_STATE_DIR": STATE,
       "LLAMA_SERVER_BIN": BIN + "/llama-server", "AIDER_BIN": BIN + "/aider", "LOCAL_EDIT_IDLE_S": "3",
       "STUB_LOG": T + "/aider.log"}


class Session:
    def __init__(self, env=ENV):
        self.p = subprocess.Popen([sys.executable, SERVER], cwd=REPO, env=env, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True)
        self.n = 0

    def call(self, args):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": "tools/call",
                                       "params": {"name": "local_edit", "arguments": args}}) + "\n")
        self.p.stdin.flush()
        res = json.loads(self.p.stdout.readline())["result"]
        return res["isError"], json.loads(res["content"][0]["text"])

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=30)


def serving():
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=1).close()
        return True
    except OSError:
        return False


print("edits")
s = Session()
err, out = s.call({"instruction": "RENAME old_name new_name", "files": ["src/a.py", "src/b.py"], "test_cmd": "grep -q new_name src/b.py"})
check("edit succeeds", not err and out["ok"], out)
check("both files reported with counts", sorted(c["file"] for c in out["changed"]) == ["src/a.py", "src/b.py"] and [c["added"] for c in sorted(out["changed"], key=lambda c: c["file"])] == [1, 2], out)
check("diff shows the change", "+def new_name():" in out["diff"], out.get("diff"))
check("test result reported", out["test"]["passed"], out.get("test"))
argv = json.loads(open(T + "/aider.log").read().splitlines()[-1])
check("aider gets the test command, no commits, local base url",
      "--auto-test" in argv and "--no-auto-commits" in argv and f"http://127.0.0.1:{PORT}/v1" in argv, argv)
pid1 = open(STATE + "/server.pid").read()

err, out = s.call({"instruction": "RENAME new_name other", "files": ["src/a.py"], "test_cmd": "false"})
check("failing test makes ok false", err and out["test"]["passed"] is False and out["changed"], out)
check("the running server is reused", open(STATE + "/server.pid").read() == pid1)

err, out = s.call({"instruction": "NOTHING", "files": ["src/a.py"]})
check("no change is an error", err and "changed none" in out.get("error", ""), out)
err, out = s.call({"instruction": "RENAME x y", "files": ["/etc/hosts"]})
check("files outside the repository are refused", err and "not inside a git repository" in out.get("error", "") or "inside the repository" in out.get("error", ""), out)
err, out = s.call({"instruction": "RENAME x y", "files": ["src/a.py", "../outside.py"]})
check("a path escaping the repository is refused", err and "inside the repository" in out.get("error", ""), out)

err, out = s.call({"instruction": "RENAME x y", "files": [MAIN + "/src/a.py"]})
check("a main checkout is refused (gpr worktrees only)", err and "main checkout" in out.get("error", ""), out)

print("unloading")
t0 = time.time()
while (serving() or os.path.exists(STATE + "/server.pid")) and time.time() - t0 < 20:
    time.sleep(0.5)
check("the model server stops after the idle time", not serving() and not os.path.exists(STATE + "/server.pid"), round(time.time() - t0))
err, out = s.call({"instruction": "RENAME other final", "files": ["src/a.py"]})
check("and loads again on the next edit", not err and serving(), out)
s.close()
time.sleep(1)
check("closing the session stops the server", not serving())

print("unavailable")
s = Session({**ENV, "LOCAL_EDIT_MODEL_FILE": T + "/missing.gguf"})
err, out = s.call({"instruction": "RENAME a b", "files": ["src/a.py"]})
check("no model file: unavailable, make the edit yourself", err and "32 GB" in out.get("error", ""), out)
s.close()

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
