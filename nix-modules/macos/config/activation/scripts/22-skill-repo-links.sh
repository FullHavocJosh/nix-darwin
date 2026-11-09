    # Convenience symlinks to the whole model-skills repos (for browsing/editing the
    # source directly), alongside the per-skill symlinks above.
    _link_whole_repo() {
      local repo="$1"
      local name
      name=$(basename "$repo")
      [ -d "$repo" ] || return 0
      local target="$HOME/.claude/skills/$name"
      if [ ! -L "$target" ] || [ "$(readlink "$target")" != "$repo" ]; then
        echo "Linking model-skills repo: $name → $repo"
        ln -sfn "$repo" "$target"
      fi
    }
    _link_whole_repo "$HOME/model-skills-fullhavoc"
    _link_whole_repo "$HOME/model-skills-perfectserve"
    unset -f _link_whole_repo

