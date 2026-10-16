"""Tests for bigpickle_mcp.py (edits by OpenCode Zen Big Pickle). A stub `opencode` stands in for the real one: no
network, no Zen calls. Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_bigpickle_mcp.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(os.path.dirname(HERE), "bigpickle_mcp.py")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="bigpickle-"))
MAIN, WT, HOME, BIN = T + "/main", T + "/wt", T + "/home", T + "/bin"
for d in (MAIN + "/src", HOME, BIN):
    os.makedirs(d)
open(MAIN + "/src/a.py", "w").write("def old_name():\n    return 1\n")
subprocess.run(f"cd {MAIN} && git init -q && git add . && git -c user.name=t -c user.email=t@t commit -qm i"
               f" && git worktree add -q -b w {WT}", shell=True)
# stub opencode: records argv, cwd and HERDR_* env; "RENAME x y" in the prompt renames in src/a.py
open(BIN + "/opencode", "w").write("""#!/usr/bin/env python3
import json, os, re, sys
open(os.environ['STUB_LOG'], 'a').write(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd(),
    'herdr': [k for k in os.environ if k.startswith('HERDR_')]}) + '\\n')
m = re.search(r'RENAME (\\w+) (\\w+)', sys.argv[-1])
if m:
    t = open('src/a.py').read(); open('src/a.py', 'w').write(t.replace(m.group(1), m.group(2)))
print('done')
""")
os.chmod(BIN + "/opencode", 0o755)
LOG = T + "/opencode.log"


def call(args, key=True, cwd=WT):
    env = {k: v for k, v in os.environ.items() if k != "OPENCODE_ZEN_API_KEY"}
    env.update(HOME=HOME, OPENCODE_BIN=BIN + "/opencode", STUB_LOG=LOG, HERDR_PANE_ID="p1", HERDR_SOCKET_PATH="/x")
    if key:
        env["OPENCODE_ZEN_API_KEY"] = "k"
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "bigpickle_edit", "arguments": args}}
    p = subprocess.run([sys.executable, SERVER], input=json.dumps(req) + "\n", capture_output=True, text=True, cwd=cwd, env=env)
    res = json.loads(p.stdout.splitlines()[0])["result"]
    return res["isError"], json.loads(res["content"][0]["text"])


r = subprocess.run([sys.executable, SERVER], input='{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n', capture_output=True, text=True)
tools = json.loads(r.stdout)["result"]["tools"]
check("tools/list: bigpickle_edit, loaded upfront", [t["name"] for t in tools] == ["bigpickle_edit"] and tools[0]["_meta"]["anthropic/alwaysLoad"] is True, tools)

err, out = call({"instruction": "RENAME old_name new_name", "files": ["src/a.py"], "test_cmd": "grep -q new_name src/a.py"})
check("edit succeeds with the shared result format", not err and out["ok"] and out["changed"][0]["file"] == "src/a.py" and "+def new_name():" in out["diff"] and out["test"]["passed"], out)
rec = json.loads(open(LOG).read().splitlines()[-1])
check("runs opencode run --auto with Big Pickle in the worktree", rec["argv"][:4] == ["run", "--auto", "--model", "opencode/big-pickle"] and os.path.realpath(rec["cwd"]) == WT, rec)
check("the prompt names the files and the test command", "src/a.py" in rec["argv"][-1] and "grep -q new_name src/a.py" in rec["argv"][-1], rec["argv"][-1])
check("HERDR_* variables are not passed to OpenCode", rec["herdr"] == [], rec["herdr"])

err, out = call({"instruction": "RENAME a b", "files": ["src/a.py"]}, key=False)
check("no Zen key: unavailable", err and "no OpenCode Zen API key" in out["error"], out)
err, out = call({"instruction": "RENAME a b", "files": [MAIN + "/src/a.py"]}, cwd=MAIN)
check("a main checkout is refused (gpr worktrees only)", err and "main checkout" in out["error"], out)
err, out = call({"instruction": "NOTHING", "files": ["src/a.py"]})
check("no change is an error", err and "changed none" in out.get("error", ""), out)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
