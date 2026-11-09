    #!/usr/bin/env bash
    set -euo pipefail

    SETTINGS_FILE="$HOME/.claude/settings.json"
    COMMANDS_DIR="$HOME/.claude/commands"
    SETUP_MARKER="$HOME/.claude/.claudetui-configured"

    if [ -f "$SETUP_MARKER" ] && [ -f "$SETTINGS_FILE" ]; then
      if grep -q '"statusLine"' "$SETTINGS_FILE" && \
         grep -q 'claudetui statusline' "$SETTINGS_FILE" && \
         [ -L "$COMMANDS_DIR/tui" ]; then
        exit 0
      fi
    fi

    echo "[claude-tui] Configuring Claude Code integration..."

    if [ ! -d "$HOME/.claude" ]; then
      echo "[claude-tui] WARNING: ~/.claude directory not found — Claude Code may not be installed"
      exit 0
    fi

    if ! command -v claudetui &>/dev/null; then
      echo "[claude-tui] WARNING: claudetui command not found — installation may be incomplete"
      exit 0
    fi

    export STATUSLINE_MODE="compact"
    export PATH="/opt/homebrew/bin:$PATH"
    SETUP_SCRIPT=$(mktemp)
    cat > "$SETUP_SCRIPT" << 'SETUPEOF'
#!/usr/bin/env bash
set -euo pipefail

SETTINGS_FILE="$HOME/.claude/settings.json"
COMMANDS_DIR="$HOME/.claude/commands"
INSTALL_DIR="${INSTALL_DIR:-/opt/homebrew/opt/claude-tui/libexec}"

python3 << 'PYEOF'
import json
import os
from pathlib import Path

settings_file = os.path.expanduser("~/.claude/settings.json")

settings = {}
if os.path.exists(settings_file):
    try:
        with open(settings_file) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError):
        backup = settings_file + ".backup"
        if os.path.exists(settings_file):
            os.rename(settings_file, backup)

mode = os.environ.get("STATUSLINE_MODE", "compact")
statusline_cmd = "claudetui statusline"
if mode == "compact":
    statusline_cmd += " --compact"

settings["statusLine"] = {
    "type": "command",
    "command": statusline_cmd,
    "refreshInterval": 10,
}

# claudetui's hooks (session heatmap, edit churn, edit deps) are not installed: they added ~1.5K tokens to every
# session start and notes to most edits, re-read on every later turn, for advice that was rarely acted on.

Path(settings_file).parent.mkdir(parents=True, exist_ok=True)
tmp = settings_file + ".tmp"
with open(tmp, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
os.replace(tmp, settings_file)
PYEOF

mkdir -p "$COMMANDS_DIR"
if [ -L "$COMMANDS_DIR/tui" ]; then
    rm "$COMMANDS_DIR/tui"
fi
ln -sfn "$INSTALL_DIR/claude-code-commands/tui" "$COMMANDS_DIR/tui"

echo "[claude-tui] Configuration complete"
SETUPEOF

    chmod +x "$SETUP_SCRIPT"
    bash "$SETUP_SCRIPT"
    rm -f "$SETUP_SCRIPT"

    touch "$SETUP_MARKER"
    echo "[claude-tui] Setup completed successfully"
