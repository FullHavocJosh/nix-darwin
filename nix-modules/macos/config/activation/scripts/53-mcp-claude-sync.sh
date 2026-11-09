    MCP_CONFIG="$HOME/nix-darwin/.config/mcp/claude-desktop-mcp.json"
    if command -v claude &>/dev/null && command -v jq &>/dev/null && [ -f "$MCP_CONFIG" ]; then
      echo "Syncing MCP servers from $MCP_CONFIG to Claude Code..."
      jq -r '.mcpServers | keys[]' "$MCP_CONFIG" | while read -r SERVER_NAME; do
        case " $MCP_EXCLUDE_SERVERS " in
          *" $SERVER_NAME "*)
            if grep -q "\"$SERVER_NAME\"" "$HOME/.claude.json" 2>/dev/null; then
              claude mcp remove --scope user "$SERVER_NAME" 2>/dev/null && \
                echo "  Removed $SERVER_NAME (excluded on this profile)." || \
                echo "  Failed to remove $SERVER_NAME."
            else
              echo "  $SERVER_NAME excluded on this profile, skipping."
            fi
            continue
            ;;
        esac

        if grep -q "\"$SERVER_NAME\"" "$HOME/.claude.json" 2>/dev/null; then
          # Two registrations that can never work: a command whose __HOME__ placeholder was never substituted
          # (ENOENT on a literal "__HOME__/..." path, seen on token-savior), and credential env values stored
          # empty because ${VAR} was expanded by the activation shell, where those variables are not set. Drop
          # them; they are registered again below with the ${VAR} placeholder stored literally.
          if jq -e --arg s "$SERVER_NAME" '((.mcpServers[$s].command // "") | contains("__HOME__")) or ([.mcpServers[$s].env // {} | to_entries[] | select(.value == "")] | length > 0)' "$HOME/.claude.json" >/dev/null 2>&1; then
            echo "  $SERVER_NAME was registered with an unsubstituted __HOME__ or empty env values; re-registering."
            claude mcp remove --scope user "$SERVER_NAME" 2>/dev/null || true
          else
            echo "  $SERVER_NAME already registered, skipping."
            continue
          fi
        fi

        COMMAND=$(jq -r ".mcpServers[\"$SERVER_NAME\"].command | gsub(\"__HOME__\"; \"$HOME\")" "$MCP_CONFIG")
        ARGS=$(jq -r ".mcpServers[\"$SERVER_NAME\"].args // [] | map(\"'\" + gsub(\"__HOME__\"; \"$HOME\") + \"'\") | join(\" \")" "$MCP_CONFIG")
        ENV_PAIRS=$(jq -r ".mcpServers[\"$SERVER_NAME\"].env // {} | to_entries | map(\"-e '\" + .key + \"=\" + (.value | gsub(\"__HOME__\"; \"$HOME\")) + \"'\") | join(\" \")" "$MCP_CONFIG")

        CMD="claude mcp add --scope user $SERVER_NAME $ENV_PAIRS -- $COMMAND $ARGS"
        eval "$CMD" 2>/dev/null && \
          echo "  Registered $SERVER_NAME with Claude Code." || \
          echo "  Failed to register $SERVER_NAME with Claude Code."
      done
    fi

