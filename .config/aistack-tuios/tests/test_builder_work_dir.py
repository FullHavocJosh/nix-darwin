#!/usr/bin/env python3
"""
Test the billed builder permissions with a work dir: edits and file commands inside it, ~/.ai read-only, denies kept.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios" + ".py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = 0


def check(ok, name):
    global FAILS
    if ok:
        print("PASS: " + name)
    else:
        print("FAIL: " + name)
        FAILS += 1


with tempfile.TemporaryDirectory() as tmp:
    wdir = os.path.join(tmp, ".worktrees", "w1")
    os.makedirs(wdir)
    wd = os.path.realpath(wdir)
    p = a.builder_permissions(None, '/s/st', work_dir=wdir)

allow = p['allow']
deny = p['deny']

for tool in ("Edit", "MultiEdit", "Write"):
    entry = f"{tool}(//{wd.lstrip('/')}/**)"
    check(entry in allow, "allow " + entry)

for entry in [f"Bash(mkdir -p {wd}/*)", f"Bash(touch {wd}/*)", f"Bash(mv {wd}/* {wd}/*)",
              f"Bash(cp {wd}/* {wd}/*)", f"Bash(rm {wd}/*)", f"Bash(rm -r {wd}/*)"]:
    check(entry in allow, "allow " + entry)

ai = os.path.expanduser('~/.ai').lstrip('/')
check(f"Read(//{ai}/**)" in allow, "allow Read of ~/.ai")
for tool in ("Edit", "MultiEdit", "Write"):
    check(f"{tool}(//{ai}/**)" in deny, f"deny {tool} of ~/.ai")

for path in ("//s/st/plan/**", "//s/st/runs/*/plan/**", "//s/st/runs/*/state.json", "//s/st/runs/*/events.jsonl"):
    for tool in ("Edit", "MultiEdit"):
        check(f"{tool}({path})" in deny, f"deny {tool}({path})")

for entry in ("Bash(rm -rf *)", "Bash(gh *)", "Bash(sudo *)", "Bash(git push *)", "Bash(git commit *)"):
    check(entry in deny, "deny " + entry)

writers = [e for e in allow if e.startswith(("Edit(", "MultiEdit(", "Write(", "Bash(mkdir", "Bash(touch", "Bash(mv",
                                              "Bash(cp", "Bash(rm"))]
check(bool(writers) and all(wd in e for e in writers), "write-capable allow entries stay in the work dir")

default = a.builder_permissions(None, '/s/st')
check(default == a.builder_permissions(None, '/s/st', work_dir=None), "work_dir=None equals the default")
check(not any(e.startswith("Write(") for e in default['allow'] + default['deny']), "default has no Write( entry")

plain = a.builder_permissions(None)["allow"]
for entry in ("Bash(fd *)", "Bash(jq *)", "Bash(sort *)", "Bash(uniq *)", "Bash(stat *)", "Bash(file *)",
              "Bash(tree *)", "Bash(pwd *)", "Bash(which *)", "Bash(test *)", "Bash(git branch --list *)",
              "Bash(git ls-files *)", "Bash(git blame *)", "Bash(git rev-parse *)", "Bash(git diff-tree *)",
              "Bash(git grep *)", "Bash(git ls-tree *)", "Bash(git remote -v *)"):
    check(entry in plain, "read-only allow " + entry)
check("mcp__tuios__tuios_send_agent_message" in plain, "tuios send message tool allowed")
check(not any(e.startswith(("Bash(git commit", "Bash(git push", "Bash(rm", "Bash(echo")) for e in plain),
      "no write command in the default allow")

with tempfile.TemporaryDirectory() as tmp:
    base = os.path.join(tmp, "settings.json")
    a.wj(base, {})
    sb = {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False}
    out = a.write_working_settings({"claude_settings": base}, os.path.join(tmp, "b.json"), sandbox=sb)
    check(a.rj(out, {}).get("sandbox") == sb, "write_working_settings writes the sandbox dict")
    out = a.write_working_settings({"claude_settings": base}, os.path.join(tmp, "c.json"))
    check("sandbox" not in a.rj(out, {}), "no sandbox key without sandbox")

saved_sock = os.environ.get("TUIOS_SOCKET")
try:
    os.environ["TUIOS_SOCKET"] = "/tmp/x/t.sock"
    sbx = a.builder_sandbox()
    check(sbx["network"]["allowUnixSockets"] == [os.path.realpath("/tmp/x/t.sock")], "sandbox allows the TUIOS_SOCKET path")
    check(sbx["enabled"] is True and sbx["allowUnsandboxedCommands"] is False, "sandbox enabled, no unsandboxed commands")
    check("allowAllUnixSockets" not in sbx and "allowAllUnixSockets" not in sbx["network"],
          "sandbox has no allowAllUnixSockets")
    os.environ.pop("TUIOS_SOCKET", None)
    check(a.builder_sandbox()["network"]["allowUnixSockets"] == [os.path.realpath("/tmp/tuios-%d/tuios.sock" % os.getuid())],
          "sandbox falls back to /tmp/tuios-<uid>/tuios.sock")
finally:
    if saved_sock is None:
        os.environ.pop("TUIOS_SOCKET", None)
    else:
        os.environ["TUIOS_SOCKET"] = saved_sock

sys.exit(1 if FAILS else 0)
