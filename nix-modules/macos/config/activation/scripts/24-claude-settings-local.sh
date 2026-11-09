    if [ ! -L "$HOME/.claude/settings.local.json" ] || [ "$(readlink "$HOME/.claude/settings.local.json")" != "$HOME/nix-darwin/.claude/settings.local.json" ]; then
      echo "Creating symlink for Claude Code settings..."
      ln -sf "$HOME/nix-darwin/.claude/settings.local.json" "$HOME/.claude/settings.local.json"
    fi

