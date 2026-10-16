"""Tests for oczen_mcp.py (one targeted file edit by OpenCode Zen Big Pickle). A stub `opencode` stands in for the real
one: no network, no Zen calls. Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_oczen_mcp.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(os.path.dirname(HERE), "oczen_mcp.py")
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="oczen-"))
MAIN, WT, HOME, BIN = T + "/main", T + "/wt", T + "/home", T + "/bin"
for d in (MAIN + "/src", HOME, BIN):
    os.makedirs(d)
ORIG = "".join(f"v{i} = {i}\n" for i in range(1, 13))
open(MAIN + "/src/a.py", "w").write(ORIG)
open(MAIN + "/src/b.py", "w").write("keep = 1\n")
subprocess.run(f"cd {MAIN} && git init -q && git add . && git -c user.name=t -c user.email=t@t commit -qm i"
               f" && git worktree add -q -b w {WT}", shell=True)
# stub opencode: records argv, cwd, HERDR_* and the config override; the prompt's keyword picks what it does
open(BIN + "/opencode", "w").write("""#!/usr/bin/env python3
import json, os, sys
prompt = sys.argv[-1]
open(os.environ['STUB_LOG'], 'a').write(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd(),
    'herdr': [k for k in os.environ if k.startswith('HERDR_')], 'config': os.environ.get('OPENCODE_CONFIG_CONTENT')}) + '\\n')
lines = open('src/a.py').read().splitlines(keepends=True)
if 'INSIDE' in prompt or 'OUTSIDE' in prompt:
    lines[9] = 'v10 = 100\\n'
if 'OUTSIDE' in prompt:
    lines[0] = 'v1 = 999\\n'
open('src/a.py', 'w').write(''.join(lines))
if 'OTHERFILES' in prompt:
    open('src/b.py', 'w').write('keep = 2\\n'); open('src/stray.py', 'w').write('x = 1\\n')
print('done')
""")
os.chmod(BIN + "/opencode", 0o755)
LOG = T + "/opencode.log"


def call(args, key=True, cwd=WT):
    env = {k: v for k, v in os.environ.items() if k != "OPENCODE_ZEN_API_KEY"}
    env.update(HOME=HOME, OPENCODE_BIN=BIN + "/opencode", STUB_LOG=LOG, HERDR_PANE_ID="p1", HERDR_SOCKET_PATH="/x")
    if key:
        env["OPENCODE_ZEN_API_KEY"] = "k"
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "oczen_edit", "arguments": args}}
    p = subprocess.run([sys.executable, SERVER], input=json.dumps(req) + "\n", capture_output=True, text=True, cwd=cwd, env=env)
    res = json.loads(p.stdout.splitlines()[0])["result"]
    return res["isError"], json.loads(res["content"][0]["text"])


def a_py():
    return open(WT + "/src/a.py").read()


def reset():
    subprocess.run(["git", "-C", WT, "checkout", "-q", "--", "."])
    subprocess.run(["git", "-C", WT, "clean", "-qfd"])


r = subprocess.run([sys.executable, SERVER], input='{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n', capture_output=True, text=True)
tools = json.loads(r.stdout)["result"]["tools"]
check("tools/list: oczen_edit, loaded upfront", [t["name"] for t in tools] == ["oczen_edit"] and tools[0]["_meta"]["anthropic/alwaysLoad"] is True, tools)
check("the schema takes one file and a line range", set(tools[0]["inputSchema"]["properties"]) == {"instruction", "file", "start_line", "end_line", "test_cmd"}, tools[0]["inputSchema"])

err, out = call({"instruction": "INSIDE", "file": "src/a.py", "start_line": 8, "end_line": 12, "test_cmd": "grep -q 'v10 = 100' src/a.py"})
check("an edit inside the range succeeds", not err and out["ok"] and "+v10 = 100" in out["diff"] and out["test"]["passed"], out)
check("the result names the file and the lines", out["changed"][0]["file"] == "src/a.py" and out["changed"][0]["lines"] == "8-12", out)
rec = json.loads(open(LOG).read().splitlines()[-1])
check("runs opencode run --standalone --auto with Big Pickle in the worktree",
      rec["argv"][:5] == ["run", "--standalone", "--auto", "--model", "opencode/big-pickle"] and os.path.realpath(rec["cwd"]) == WT, rec)
check("OpenCode's formatter is off", json.loads(rec["config"] or "{}").get("formatter") is False, rec["config"])
check("the prompt names the range, the file and the current lines", "lines 8-12 of src/a.py" in rec["argv"][-1] and "v8 = 8" in rec["argv"][-1], rec["argv"][-1])
check("the prompt carries the test command", "grep -q 'v10 = 100' src/a.py" in rec["argv"][-1], rec["argv"][-1])
check("HERDR_* variables are not passed to OpenCode", rec["herdr"] == [], rec["herdr"])
reset()

err, out = call({"instruction": "OUTSIDE", "file": "src/a.py", "start_line": 8, "end_line": 12})
check("a change outside the range is an error", err and "outside 8-12" in out.get("error", ""), out)
check("and the file is put back", a_py() == ORIG, a_py())
reset()

err, out = call({"instruction": "INSIDE OTHERFILES", "file": "src/a.py", "start_line": 8, "end_line": 12})
check("other files it touched are restored or removed", sorted(out.get("undone", [])) == ["src/b.py", "src/stray.py"]
      and open(WT + "/src/b.py").read() == "keep = 1\n" and not os.path.exists(WT + "/src/stray.py"), out)
check("the target file keeps its edit", "v10 = 100" in a_py(), a_py())
reset()

err, out = call({"instruction": "INSIDE", "file": "src/a.py"}, key=False)
check("no Zen key: unavailable", err and "no OpenCode Zen API key" in out["error"], out)
err, out = call({"instruction": "INSIDE", "file": MAIN + "/src/a.py"}, cwd=MAIN)
check("a main checkout is refused (gpr worktrees only)", err and "main checkout" in out["error"], out)
err, out = call({"instruction": "INSIDE", "files": ["src/a.py", "src/b.py"]})
check("several files in one call are refused (one file per call)", err and "one file per call" in out["error"], out)
err, out = call({"instruction": "NOTHING", "file": "src/a.py"})
check("no change is an error", err and "changed nothing" in out.get("error", ""), out)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
