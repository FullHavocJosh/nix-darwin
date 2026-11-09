set -euo pipefail
mkdir -p "$HOME/.claude/output-styles" "$HOME/.local/bin"
ln -sfn "$HOME/.config/aistack/advisor-style.md" "$HOME/.claude/output-styles/advisor.md"
ln -sfn "$HOME/.config/aistack/advisor_hook.py" "$HOME/.local/bin/advisor"
path="$HOME/.claude/settings.json"
[ -f "$path" ] || exit 0
python3 - "$path" <<'PYEOF'
import json, os, sys
path = sys.argv[1]
with open(path) as f:
    settings = json.load(f)
before = json.dumps(settings, sort_keys=True)
hook = "python3 \"$HOME/.config/aistack/advisor_hook.py\""
pre = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
if not any(h.get("command") == hook for r in pre for h in r.get("hooks", [])):
    pre.append({"matcher": ".*", "hooks": [{"type": "command", "command": hook, "timeout": 10}]})
settings.setdefault("outputStyle", "Advisor")
if json.dumps(settings, sort_keys=True) != before:
    with open(path + ".tmp", "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    os.replace(path + ".tmp", path)
    print("[claude] Updated settings.json: advisor mode on (hook and output style)")
PYEOF
