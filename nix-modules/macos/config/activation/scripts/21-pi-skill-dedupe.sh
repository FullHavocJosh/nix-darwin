    # pi scans both ~/.pi/agent/skills and ~/.agents/skills, so a skill present in both shows up as a
    # "[Skill conflicts]" collision at startup. ~/.agents/skills is the copy ~/.agents/.skill-lock.json
    # tracks, so drop the pi copy -- only when it is a real directory identical to the tracked one.
    if [ -d "$HOME/.pi/agent/skills" ] && [ -d "$HOME/.agents/skills" ]; then
      for pi_skill in "$HOME/.pi/agent/skills"/*/; do
        pi_skill="${pi_skill%/}"
        [ -d "$pi_skill" ] && [ ! -L "$pi_skill" ] || continue
        shared_skill="$HOME/.agents/skills/$(basename "$pi_skill")"
        [ -d "$shared_skill" ] || continue
        if diff -rq "$pi_skill" "$shared_skill" >/dev/null 2>&1; then
          echo "Removing duplicate pi skill (same as $shared_skill): $pi_skill"
          rm -r "$pi_skill"
        fi
      done
      rmdir "$HOME/.pi/agent/skills" 2>/dev/null || true
    fi

