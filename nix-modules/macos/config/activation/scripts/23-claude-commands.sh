    mkdir -p "$HOME/.claude/commands"
    _link_commands_from_repo() {
      local repo="$1"
      [ -d "$repo/.claude/commands" ] || return 0
      for cmd_file in "$repo/.claude/commands"/*.md; do
        [ -f "$cmd_file" ] || continue
        local cmd_name
        cmd_name=$(basename "$cmd_file")
        local target="$HOME/.claude/commands/$cmd_name"
        if [ ! -L "$target" ] || [ "$(readlink "$target")" != "$cmd_file" ]; then
          echo "Linking Claude command: $cmd_name"
          ln -sfn "$cmd_file" "$target"
        fi
      done
    }
    _link_commands_from_repo "$HOME/model-skills-fullhavoc"
    _link_commands_from_repo "$HOME/model-skills-perfectserve"
    unset -f _link_commands_from_repo

