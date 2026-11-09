    if command -v uv &>/dev/null; then
      if ! uv tool list 2>/dev/null | grep -q "^unmcp "; then
        echo "Installing unmcp CLI tool..."
        uv tool install unmcp 2>&1 || echo "Failed to install unmcp"
      fi
      if ! uv tool list 2>/dev/null | grep -q "^claude-code-config "; then
        echo "Installing claude-code-config..."
        uv tool install claude-code-config 2>&1 || echo "Failed to install claude-code-config"
      fi
    fi

