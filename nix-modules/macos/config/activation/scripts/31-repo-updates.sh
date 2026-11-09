    if command -v git &>/dev/null; then
      _update_repo_main() {
        local repo_path="$1"
        local repo_name
        repo_name=$(basename "$repo_path")

        if [ ! -d "$repo_path/.git" ]; then
          echo "  $repo_name: not present, skipping."
          return 0
        fi

        echo "── $repo_name ──"

        local current_branch
        current_branch=$(git -C "$repo_path" symbolic-ref --short HEAD 2>/dev/null)
        if [ -z "$current_branch" ]; then
          echo "  Detached HEAD, skipping."
          return 0
        fi

        local stash_created=0
        if ! git -C "$repo_path" diff --quiet HEAD 2>/dev/null; then
          git -C "$repo_path" stash push -m "darwin-rebuild auto-stash $(date +%Y%m%d-%H%M%S)" \
            && stash_created=1 \
            && echo "  Stashed uncommitted changes."
        fi

        # Prefer the remote's default branch (origin/HEAD), so repos whose
        # default isn't main/master (e.g. azerothcore-wotlk on Playerbot)
        # still get updated; fall back to local main/master.
        local main_branch
        main_branch=$(git -C "$repo_path" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||' || true)
        if [ -z "$main_branch" ]; then
          if git -C "$repo_path" rev-parse --verify main &>/dev/null; then
            main_branch="main"
          elif git -C "$repo_path" rev-parse --verify master &>/dev/null; then
            main_branch="master"
          else
            echo "  No default branch (origin/HEAD, main, master) found, skipping."
            [ "$stash_created" -eq 1 ] && git -C "$repo_path" stash pop
            return 0
          fi
        fi

        if [ "$current_branch" != "$main_branch" ]; then
          git -C "$repo_path" checkout "$main_branch" || {
            echo "  Failed to checkout $main_branch, aborting."
            [ "$stash_created" -eq 1 ] && git -C "$repo_path" stash pop
            return 1
          }
        fi

        git -C "$repo_path" pull \
          || echo "  Warning: pull failed for $repo_name (SSH agent may not be available)."
        git -C "$repo_path" submodule update --init --recursive \
          || echo "  Warning: submodule update failed for $repo_name (private or inaccessible submodule?)."

        if [ "$current_branch" != "$main_branch" ]; then
          git -C "$repo_path" checkout "$current_branch" \
            || echo "  Warning: failed to return to $current_branch."
        fi

        if [ "$stash_created" -eq 1 ]; then
          git -C "$repo_path" stash pop \
            || echo "  Warning: stash pop failed — run: git -C '$repo_path' stash pop"
        fi

        echo "  Done."
      }

      echo "Updating tracked repositories to latest main..."
      # Dynamically discovers every repo directly under $HOME (anything with a
      # .git entry) instead of a hardcoded list -- so a newly cloned repo gets
      # picked up automatically on the next darwin-rebuild without editing this
      # file. Nested repos (2+ levels deep) are intentionally not touched here.
      for REPO_GIT_DIR in "$HOME"/*/.git; do
        [ -e "$REPO_GIT_DIR" ] || continue
        _update_repo_main "${REPO_GIT_DIR%/.git}"
      done
      unset -f _update_repo_main
      echo "Finished updating repositories."
    fi

