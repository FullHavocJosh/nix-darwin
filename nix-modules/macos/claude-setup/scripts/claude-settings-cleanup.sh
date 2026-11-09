set -euo pipefail
path="$HOME/.claude/settings.json"
[ -f "$path" ] || exit 0
python3 - "$path" <<'PYEOF'
import json, os, sys
path = sys.argv[1]
with open(path) as f:
    settings = json.load(f)
before = json.dumps(settings, sort_keys=True)
def retired(cmd):
    return "token-optimizer" in cmd or cmd.startswith("claudetui hook")
hooks = settings.get("hooks", {})
for event in list(hooks):
    kept = []
    for rule in hooks[event]:
        rule["hooks"] = [h for h in rule.get("hooks", []) if not retired(h.get("command", ""))]
        if rule["hooks"]:
            kept.append(rule)
    if kept:
        hooks[event] = kept
    else:
        del hooks[event]
deny = settings.setdefault("permissions", {}).setdefault("deny", [])
if "WebSearch" not in deny:
    deny.append("WebSearch")
# The free tools that take work from Claude run without a permission prompt.
allow = settings["permissions"].setdefault("allow", [])
if "mcp__bigpickle__bigpickle_edit" in allow:  # renamed to oczen_edit
    allow.remove("mcp__bigpickle__bigpickle_edit")
for tool in ("mcp__lumo__lumo_search", "mcp__local-edit__local_edit", "mcp__oczen__oczen_edit"):
    if tool not in allow:
        allow.append(tool)
# edit_router_hook.py: the third file edited by hand in one request goes to local_edit / oczen_edit.
router = "python3 \"$HOME/.config/aistack/edit_router_hook.py\""
if not any(h.get("command") == router for r in hooks.get("PreToolUse", []) for h in r.get("hooks", [])):
    hooks.setdefault("PreToolUse", []).append(
        {"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [{"type": "command", "command": router, "timeout": 10}]})
    settings["hooks"] = hooks
if json.dumps(settings, sort_keys=True) != before:
    with open(path + ".tmp", "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    os.replace(path + ".tmp", path)
    print("[claude] Updated settings.json: retired hooks removed, WebSearch denied, edit routing enforced")
PYEOF
