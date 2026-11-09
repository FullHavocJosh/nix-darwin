    OPENCODE_CONFIG="$HOME/.config/opencode/opencode.json"
    REPO_OPENCODE_CONFIG="$HOME/nix-darwin/.config/opencode/opencode.json"
    if command -v jq &>/dev/null && [ -f "$REPO_OPENCODE_CONFIG" ]; then
      mkdir -p "$(dirname "$OPENCODE_CONFIG")"
      # Hard safety net: never rm+cp when the two paths are still the same
      # file (device+inode, via -ef) -- that's exactly the condition under
      # which rm would delete the git-tracked source out from under the
      # following cp, corrupting the repo's working tree. If the unfold
      # above ever regresses, fail loud here instead of deleting data.
      if [ -e "$OPENCODE_CONFIG" ] && [ "$OPENCODE_CONFIG" -ef "$REPO_OPENCODE_CONFIG" ]; then
        echo "Warning: $OPENCODE_CONFIG still resolves to the git-tracked file (unfold didn't take); skipping OpenCode config deployment this run to avoid corrupting the repo."
      else
        rm -f "$OPENCODE_CONFIG"
        cp "$REPO_OPENCODE_CONFIG" "$OPENCODE_CONFIG"
        # Skill directories are no longer injected into .skills.paths here --
        # the opencode-skillful plugin (see .config/opencode-skillful/config.json)
        # discovers them lazily via its own basePaths instead. This loop used to
        # unconditionally re-add $HOME/model-skills-* on every activation, which
        # silently reintroduced eager skill loading (and the ~17K token cost that
        # comes with it) on every darwin-rebuild regardless of what opencode.json's
        # own skills.paths was committed as.

        # OpenCode starts every MCP server it is given when it launches, which costs far more context than Claude
        # Code, which loads tools on demand. So OpenCode gets two kinds of entries: the always-needed servers in the
        # repo's opencode.json (mcp-stack-fullhavoc, plus context-guardian-perfectserve on the work profile), and one
        # mcp-lazy proxy that exposes two tools and starts each upstream server only when one of its tools is first
        # used. The proxy's server list, ~/.mcp-lazy/servers.json, is rebuilt on every rebuild from the servers Claude
        # Code has registered (profile exclusions already applied) minus the ones opencode.json loads directly, so
        # both tools offer the same servers. mcp-lazy starts upstream servers with its own environment plus the env in
        # servers.json and does not expand ${VAR}: credentials are left out of servers.json and are handed to the
        # proxy by name through its `environment` below ({env:NAME}, resolved by OpenCode at launch from the exports
        # in ~/.zshrc_personal). The tool index is cached by mcp-lazy; the first session after a change is slower.
        MCP_LAZY_JQ="$HOME/nix-darwin/.config/mcp/claude-to-mcp-lazy.jq"
        MCP_LAZY_SUPERSEDED='["lumo","local-edit","oczen"]'
        if [ -f "$HOME/.claude.json" ] && [ -f "$MCP_LAZY_JQ" ]; then
          if LAZY=$(jq --arg home "$HOME" --argjson superseded "$MCP_LAZY_SUPERSEDED" -f "$MCP_LAZY_JQ" "$HOME/.claude.json" 2>/dev/null) && [ -n "$LAZY" ] && [ "$LAZY" != "{}" ]; then
            mkdir -p "$HOME/.mcp-lazy"
            if jq -n --argjson s "$LAZY" '{servers: $s}' > "$HOME/.mcp-lazy/servers.json.new"; then
              mv "$HOME/.mcp-lazy/servers.json.new" "$HOME/.mcp-lazy/servers.json"
              echo "mcp-lazy servers (started on demand by OpenCode): $(printf '%s' "$LAZY" | jq -r 'keys | join(", ")')"
            fi
            if [ -f "$MCP_CONFIG" ]; then
              LAZY_ENV=$(jq '[.mcpServers[].env // {} | to_entries[] | select(.value | test("^\\$\\{[A-Za-z0-9_]+\\}$")) | .key] | unique | map({(.): "{env:\(.)}"}) | add // {}' "$MCP_CONFIG" 2>/dev/null)
              if [ -n "$LAZY_ENV" ] && UPDATED=$(jq --argjson e "$LAZY_ENV" 'if .mcp["mcp-lazy"] then .mcp["mcp-lazy"].environment = ((.mcp["mcp-lazy"].environment // {}) + $e) else . end' "$OPENCODE_CONFIG" 2>/dev/null) && [ -n "$UPDATED" ]; then
                printf '%s\n' "$UPDATED" > "$OPENCODE_CONFIG"
              fi
            fi
          else
            echo "Warning: could not build the mcp-lazy server list from Claude Code; leaving ~/.mcp-lazy/servers.json as it is."
          fi
        fi

        for EXCLUDED in $MCP_EXCLUDE_SERVERS; do
          if jq -e --arg s "$EXCLUDED" '.mcp[$s]' "$OPENCODE_CONFIG" &>/dev/null; then
            UPDATED=$(jq --arg s "$EXCLUDED" '.mcp[$s].enabled = false' "$OPENCODE_CONFIG")
            printf '%s\n' "$UPDATED" > "$OPENCODE_CONFIG"
            echo "Disabled $EXCLUDED in OpenCode config (excluded on this profile)"
          fi
        done
      fi
    fi

