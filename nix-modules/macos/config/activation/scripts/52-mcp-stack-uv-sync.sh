    # mcp-stack-fullhavoc is a uv-managed Python project, not part of the
    # $HOME/mcp-* npm auto-build loop above -- sync its deps here so the
    # first real MCP handshake (Claude Code or opencode) isn't also the
    # first dependency resolve.
    if command -v uv &>/dev/null && [ -f "$HOME/mcp-stack-fullhavoc/pyproject.toml" ]; then
      echo "Syncing mcp-stack-fullhavoc dependencies..."
      uv sync --project "$HOME/mcp-stack-fullhavoc" && \
        echo "mcp-stack-fullhavoc dependencies up to date." || \
        echo "Failed to sync mcp-stack-fullhavoc dependencies"
    fi

