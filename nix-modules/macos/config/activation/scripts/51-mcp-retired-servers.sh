    # MCP servers retired from claude-desktop-mcp.json: none was called more than a handful of times in 60-90 days of
    # transcripts (token-optimizer-mcp was called, but only because its hooks forced it, and its results were larger
    # than the built-in tools'), or the package is gone (aws-core, aws-terraform, terraform-cloud, terraform-hcp, and
    # the context-guardian / verbosity-guardian servers mcp-stack-fullhavoc replaced). The sync below only adds, so
    # unregister them on every host.
    if command -v claude &>/dev/null; then
      for SERVER_NAME in token-optimizer-mcp token-savior context-mode mcp-server-chart memory sequential-thinking prettier bigpickle github aws-pricing-mcp-server aws-core-mcp-server aws-terraform-mcp terraform-cloud terraform-hcp mcp-context-guardian-fullhavoc context-guardian verbosity-guardian; do
        if jq -e --arg s "$SERVER_NAME" '.mcpServers[$s]' "$HOME/.claude.json" >/dev/null 2>&1; then
          claude mcp remove --scope user "$SERVER_NAME" >/dev/null 2>&1 && \
            echo "Removed retired MCP server $SERVER_NAME from Claude Code." || \
            echo "Failed to remove retired MCP server $SERVER_NAME."
        fi
      done
    fi

