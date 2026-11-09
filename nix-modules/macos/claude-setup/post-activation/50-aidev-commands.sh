    # Claude Code commands that move work to aidev's free model:
    #   /aidev-handoff  write an aidev plan in the session and start the run
    #   /delegate       hand one large mechanical edit to `aidev -p` and only review it
    mkdir -p "$HOME/.claude/commands"
    for CMD_FILE in aidev-handoff.md delegate.md; do
      if [ -f "$HOME/.config/aistack/$CMD_FILE" ]; then
        ln -sfn "$HOME/.config/aistack/$CMD_FILE" "$HOME/.claude/commands/$CMD_FILE"
      fi
    done

