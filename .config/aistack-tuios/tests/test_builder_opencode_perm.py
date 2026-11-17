#!/usr/bin/env python3
"""
Test the OpenCode bash permission map of the builder: ask by default, read-only and verify commands allowed, denies last.
"""
import importlib.util
import json
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


perm = a.opencode_bash_permission({"T1": ["python3 x.py"], "T2": "make test"})
keys = list(perm)
check(keys[0] == "*" and perm["*"] == "ask", "first key is '*': 'ask'")
check(perm.get("ls *") == "allow" and perm.get("fd *") == "allow", "read-only commands allowed")
check(perm.get("python3 x.py") == "allow", "verify command from a list allowed")
check(perm.get("make test") == "allow", "verify command from a string allowed")
for k in ("git push *", "git commit *", "gh *", "sudo *"):
    check(perm.get(k) == "deny", k + " denied")
deny_idx = [i for i, k in enumerate(keys) if perm[k] == "deny"]
allow_idx = [i for i, k in enumerate(keys) if perm[k] == "allow"]
check(bool(deny_idx) and bool(allow_idx) and min(deny_idx) > max(allow_idx), "deny keys come after allow keys")
check(not any(k.startswith("Bash(") for k in keys), "no Bash( wrapper left in keys")
none_perm = a.opencode_bash_permission(None)
check(none_perm["*"] == "ask" and none_perm.get("ls *") == "allow", "verify None works")

with tempfile.TemporaryDirectory() as tmp:
    src = os.path.join(tmp, "src")
    os.makedirs(os.path.join(src, "plugins"))
    src_cfg = os.path.join(src, "opencode.json")
    with open(src_cfg, "w") as fh:
        json.dump({"formatter": {}}, fh)
    with open(os.path.join(src, "plugins", "state.js"), "w") as fh:
        fh.write("// plugin")
    out = a.write_builder_opencode({"dir": tmp, "opencode_dir": src}, {"T1": ["make test"]})
    with open(os.path.join(out, "opencode.json")) as fh:
        got = json.load(fh)
    check(out != src and out == os.path.join(tmp, "opencode-build", "opencode"), "copy goes to dir/opencode-build/opencode")
    check(got.get("permission", {}).get("bash", {}).get("make test") == "allow", "copy has the permission key")
    check(got.get("formatter") == {}, "copy keeps formatter")
    check(os.path.isfile(os.path.join(out, "plugins", "state.js")), "copy keeps the plugin file")
    with open(src_cfg) as fh:
        check(json.load(fh) == {"formatter": {}}, "source config unchanged")

sys.exit(1 if FAILS else 0)
