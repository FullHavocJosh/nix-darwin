    # Claude Code scans ~/.claude/skills/ for direct subdirs with SKILL.md, not nested repos.
    # Skills are sourced from model-skills repos only; ~/.claude/skills/ is the target, never a source.
    mkdir -p "$HOME/.claude/skills"
    _link_skills_from_repo() {
      local repo="$1"
      # Never recurse into ~/.claude/skills itself — that is our target, not a source
      [ -d "$repo" ] || return 0
      [ "$(cd "$repo" && pwd -P)" = "$(cd "$HOME/.claude/skills" && pwd -P)" ] && return 0
      for skill_dir in "$repo"/*/; do
        [ -f "$skill_dir/SKILL.md" ] || continue
        local skill_name
        skill_name=$(basename "$skill_dir")
        local target="$HOME/.claude/skills/$skill_name"
        # A real directory here (for example one that a tool copied there on its own) would make
        # `ln -sfn` nest the link inside it instead of replacing it, and the repo copy would never be
        # the one Claude Code loads. Move it aside rather than delete it.
        if [ -d "$target" ] && [ ! -L "$target" ]; then
          local displaced="$HOME/.claude/.skills-displaced/$skill_name-$(date +%Y%m%d%H%M%S)"
          mkdir -p "$HOME/.claude/.skills-displaced"
          echo "Displacing real directory $target (the model-skills copy replaces it): $displaced"
          mv "$target" "$displaced"
        fi
        if [ ! -L "$target" ] || [ "$(readlink "$target")" != "$skill_dir" ]; then
          echo "Linking Claude skill: $skill_name → $skill_dir"
          ln -sfn "$skill_dir" "$target"
        fi
      done
    }
    # Loop over `*`, not `*/`: a dangling symlink does not match `*/`, so the stale links this loop exists to
    # remove were skipped.
    for existing_link in "$HOME/.claude/skills"/*; do
      [ -L "$existing_link" ] || continue
      link_name=$(basename "$existing_link")
      # Whole-repo convenience symlinks (below) have no SKILL.md of their own -- don't
      # treat them as stale skill links.
      case "$link_name" in
        model-skills-fullhavoc|model-skills-perfectserve) continue ;;
      esac
      if [ ! -f "$existing_link/SKILL.md" ]; then
        echo "Removing stale Claude skill symlink: $link_name"
        rm "$existing_link"
      fi
    done
    _link_skills_from_repo "$HOME/model-skills-fullhavoc"
    _link_skills_from_repo "$HOME/model-skills-perfectserve"
    unset -f _link_skills_from_repo

