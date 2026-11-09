    if command -v go &>/dev/null; then
      if ! command -v claude-session-manager-tui &>/dev/null; then
        echo "Installing claude-session-manager-tui..."
        # Pinned to audited commit f114e7d (2026-04-01); no tagged releases exist upstream.
        # To update: review diff from f114e7d to new commit before changing the hash.
        go install github.com/borball/claude-session-manager-tui@f114e7d7e0d78e10087692a10724f2a7383edfd3 2>&1 || echo "Failed to install claude-session-manager-tui"
      fi
    fi

