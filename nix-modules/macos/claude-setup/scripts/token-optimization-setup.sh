    #!/usr/bin/env bash
    set -uo pipefail

    MARKER_DIR="$HOME/.claude/.token-optimization"
    mkdir -p "$MARKER_DIR"

    # token-optimizer-mcp is retired (2026-10-15): over 60 days its hooks forced 119 retried tool calls, its
    # smart_edit results were ~14x the size of a built-in Edit result, and it injected text into every tool call.
    # Uninstall the package; claudeSettingsCleanup removes its hooks from ~/.claude/settings.json.
    if npm ls -g @ooples/token-optimizer-mcp &>/dev/null; then
      echo "[token-optimization] Uninstalling retired token-optimizer-mcp..."
      npm uninstall -g @ooples/token-optimizer-mcp 2>&1 || echo "WARNING: token-optimizer-mcp uninstall failed" >&2
    fi

    # --- pi: global npm install ---
    if ! npm ls -g @earendil-works/pi-coding-agent &>/dev/null; then
      echo "[token-optimization] Installing pi-coding-agent..."
      npm install -g @earendil-works/pi-coding-agent 2>&1 || echo "WARNING: pi-coding-agent install failed" >&2
    fi

    # --- caveman: Claude Code plugin (skill + hooks + statusline) ---
    if command -v claude &>/dev/null && [ ! -f "$MARKER_DIR/caveman-plugin-installed" ]; then
      echo "[token-optimization] Installing caveman plugin..."
      claude plugin marketplace add JuliusBrussee/caveman 2>&1 || true
      if claude plugin install caveman@caveman 2>&1; then
        touch "$MARKER_DIR/caveman-plugin-installed"
        echo "[token-optimization] caveman plugin installed."
      else
        echo "WARNING: caveman plugin install failed" >&2
      fi
    fi
    mkdir -p "$HOME/.config/caveman"
    if [ ! -f "$HOME/.config/caveman/config.json" ]; then
      cat > "$HOME/.config/caveman/config.json" <<'JSON'
{"defaultMode": "ultra"}
JSON
    fi
