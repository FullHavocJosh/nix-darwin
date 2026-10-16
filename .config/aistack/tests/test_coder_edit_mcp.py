"""Tests for local_edit_mcp.py (one targeted file edit on the on-device coder model). A stub llama-server stands in for
the real one: it answers chat completions from the <region> it is sent. No model, no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_coder_edit_mcp.py
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
MAIN, REPO, STATE, BIN = T + "/main", T + "/repo", T + "/state", T + "/bin"
os.makedirs(MAIN + "/src")
os.makedirs(BIN)
open(MAIN + "/src/a.py", "w").write("def old_name():\n    return 1\n")
open(MAIN + "/src/big.py", "w").write("".join(f"line_{i} = {i}\n" for i in range(1, 401)))
subprocess.run(f"cd {MAIN} && git init -q && git add . && git -c user.name=t -c user.email=t@t commit -qm init"
               f" && git worktree add -q -b work {REPO}", shell=True)
MODEL = T + "/model.gguf"
open(MODEL, "w").write("stub")
PROMPTS = T + "/prompts.jsonl"

# stub llama-server: /v1/models lists --alias; /v1/chat/completions edits the <region> per the instruction
open(BIN + "/llama-server", "w").write("""#!/usr/bin/env python3
import http.server, json, os, re, sys, time
a = sys.argv; port = int(a[a.index('--port') + 1]); alias = a[a.index('--alias') + 1]
time.sleep(0.5)
class H(http.server.BaseHTTPRequestHandler):
    def reply(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        self.reply({"data": [{"id": alias}]})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        user = body['messages'][-1]['content']
        open(os.environ['STUB_PROMPTS'], 'a').write(json.dumps({'user': user, 'max_tokens': body['max_tokens']}) + '\\n')
        region = re.search(r'<region lines="[^"]*">\\n(.*?)\\n?</region>', user, re.S).group(1)
        instr = re.search(r'Instruction: (.*)', user).group(1)
        finish = 'stop'
        if instr.startswith('RENAME'):
            _, old, new = instr.split()[:3]; out = region.replace(old, new)
        elif instr.startswith('FENCE'):
            out = '```python\\n' + region.upper() + '\\n```'
        elif instr.startswith('FAILFIX'):
            out = region.replace('BAD', 'GOOD') if 'failed this check' in user else region + '\\nBAD = 1'
        elif instr.startswith('CREATE'):
            out = 'created = True'
        elif instr.startswith('LONG'):
            out, finish = region, 'length'
        else:
            out = region
        self.reply({"choices": [{"message": {"content": out}, "finish_reason": finish}]})
    def log_message(self, *x): pass
http.server.HTTPServer(('127.0.0.1', port), H).serve_forever()
""")
os.chmod(BIN + "/llama-server", 0o755)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = free_port()
ENV = {**os.environ, "LOCAL_EDIT_MODEL_FILE": MODEL, "LOCAL_EDIT_PORT": str(PORT), "LOCAL_EDIT_STATE_DIR": STATE,
       "LLAMA_SERVER_BIN": BIN + "/llama-server", "LOCAL_EDIT_IDLE_S": "3", "STUB_PROMPTS": PROMPTS}


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


def last_prompt():
    return json.loads(open(PROMPTS).read().splitlines()[-1])


print("one file, one region")
s = Session()
err, out = s.call({"instruction": "RENAME old_name new_name", "file": "src/a.py", "test_cmd": "grep -q new_name src/a.py"})
check("small whole-file edit succeeds", not err and out["ok"] and "+def new_name():" in out["diff"] and out["test"]["passed"], out)
check("the result names the file and the lines", out["changed"][0]["file"] == "src/a.py" and out["changed"][0]["lines"] == "1-2", out)

err, out = s.call({"instruction": "RENAME line_200 renamed_200", "file": "src/big.py", "start_line": 200, "end_line": 200})
big = open(REPO + "/src/big.py").read().splitlines()
check("a line range changes exactly that range", not err and big[199] == "renamed_200 = 200" and big[198] == "line_199 = 199" and len(big) == 400, (out, big[198:201]))
p = last_prompt()["user"]
check("the model sees only the region and 5 context lines on each side",
      "line_195" in p and "line_194" not in p and "line_205" in p and "line_206" not in p and len(p) < 1200, p)
check("context lines are numbered, the region is not", "  199| line_199" in p and '<region lines="200-200">\nline_200 = 200\n</region>' in p, p)
check("max_tokens is sized to the region, not the whole window", last_prompt()["max_tokens"] <= 1024, last_prompt())

err, out = s.call({"instruction": "RENAME line_1 x", "file": "src/big.py"})
check("a large file without a range is refused, asking for start_line/end_line", err and "start_line and end_line" in out["error"], out)
err, out = s.call({"instruction": "RENAME a b", "file": "src/big.py", "start_line": 390, "end_line": 420})
check("a range past the end of the file is refused", err and "outside" in out["error"], out)
err, out = s.call({"instruction": "RENAME a b", "files": ["src/a.py", "src/big.py"]})
check("several files in one call are refused (one file per call)", err and "one file per call" in out["error"], out)

err, out = s.call({"instruction": "FENCE", "file": "src/a.py"})
check("markdown fences in the reply are stripped", not err and "```" not in open(REPO + "/src/a.py").read(), open(REPO + "/src/a.py").read())
subprocess.run(["git", "-C", REPO, "checkout", "-q", "--", "src/a.py"])

err, out = s.call({"instruction": "FAILFIX", "file": "src/a.py", "test_cmd": "! grep -q BAD src/a.py"})
check("a failing test gets one fix attempt with the failure output", not err and out["test"]["passed"] and "GOOD" in open(REPO + "/src/a.py").read(), out)
check("the fix prompt carries the failure", "failed this check" in last_prompt()["user"], last_prompt()["user"][-300:])
subprocess.run(["git", "-C", REPO, "checkout", "-q", "--", "src/a.py"])

err, out = s.call({"instruction": "CREATE", "file": "src/new/mod.py"})
check("a new file is created", not err and open(REPO + "/src/new/mod.py").read() == "created = True\n" and out["changed"][0]["created"], out)
err, out = s.call({"instruction": "LONG", "file": "src/a.py"})
check("hitting the output limit is an error", err and "output limit" in out["error"], out)
err, out = s.call({"instruction": "NOTHING", "file": "src/a.py"})
check("no change is an error", err and "changed nothing" in out.get("error", ""), out)
err, out = s.call({"instruction": "RENAME x y", "file": "/etc/hosts"})
check("files outside a repository are refused", err and "not inside a git repository" in out["error"], out)
err, out = s.call({"instruction": "RENAME x y", "file": MAIN + "/src/a.py"})
check("a main checkout is refused (gpr worktrees only)", err and "main checkout" in out["error"], out)
pid1 = open(STATE + "/server.pid").read()
s.call({"instruction": "RENAME old_name other", "file": "src/a.py"})
check("the running server is reused", open(STATE + "/server.pid").read() == pid1)

print("unloading")
t0 = time.time()
while (serving() or os.path.exists(STATE + "/server.pid")) and time.time() - t0 < 20:
    time.sleep(0.5)
check("the model server stops after the idle time", not serving() and not os.path.exists(STATE + "/server.pid"), round(time.time() - t0))
err, out = s.call({"instruction": "RENAME other final", "file": "src/a.py"})
check("and loads again on the next edit", not err and serving(), out)
s.close()
time.sleep(1)
check("closing the session stops the server", not serving())

print("unavailable")
s = Session({**ENV, "LOCAL_EDIT_MODEL_FILE": T + "/missing.gguf"})
err, out = s.call({"instruction": "RENAME a b", "file": "src/a.py"})
check("no model file: unavailable, make the edit yourself", err and "32 GB" in out.get("error", ""), out)
s.close()

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
