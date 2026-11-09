    if command -v npm &>/dev/null && command -v node &>/dev/null; then
      MCP_FOUND=0
      for MCP_DIR in "$HOME"/mcp-*/; do
        [ -d "$MCP_DIR" ] || continue
        [ -f "$MCP_DIR/package.json" ] || continue
        MCP_FOUND=1
        MCP_NAME=$(basename "$MCP_DIR")
        MCP_DIST="${MCP_DIR%/}/dist/index.js"
        echo "Checking MCP server: $MCP_NAME"
        cd "$MCP_DIR"
        if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ] || [ "package-lock.json" -nt "node_modules" ]; then
          echo "Installing dependencies for $MCP_NAME..."
          npm install --no-audit --no-fund || echo "Failed to install dependencies for $MCP_NAME"
        fi
        # Non-breaking fixes only (no --force). The rewritten package-lock.json
        # stays uncommitted and is newer than dist, so the build below reruns.
        if ! npm audit >/dev/null 2>&1; then
          echo "Applying npm audit fixes for $MCP_NAME..."
          npm audit fix --no-fund || echo "npm audit fix failed for $MCP_NAME"
        fi
        if [ ! -f "$MCP_DIST" ] || [ "src" -nt "$MCP_DIST" ] || [ "package-lock.json" -nt "$MCP_DIST" ]; then
          echo "Building $MCP_NAME..."
          npm run build && echo "$MCP_NAME built successfully!" || echo "Failed to build $MCP_NAME"
        else
          echo "$MCP_NAME is up to date."
        fi
        if [ -f "$MCP_DIST" ] && command -v claude &>/dev/null; then
          if ! grep -q "\"$MCP_NAME\"" "$HOME/.claude.json" 2>/dev/null; then
            claude mcp add --scope user "$MCP_NAME" node "$MCP_DIST" 2>/dev/null && \
              echo "Registered $MCP_NAME with Claude Code." || \
              echo "Failed to register $MCP_NAME with Claude Code."
          fi
        fi
      done
      [ "$MCP_FOUND" -eq 0 ] && echo "No ~/mcp-* servers found, skipping."
    else
      echo "Skipping MCP server builds (npm or node not available in PATH)"
    fi

