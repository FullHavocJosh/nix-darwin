# Fast-forwards $1's default branch (main or master, whichever origin/HEAD points
# at) to match origin, but ONLY if $1 is currently checked out on that branch --
# never touches a repo sitting on some other branch, which shouldn't happen under
# this workflow (real work always happens in a worktree) but is a cheap guard
# against pulling into the wrong place. --ff-only means this can never create a
# merge conflict: if local main has actually diverged (e.g. from a manual commit),
# the merge just fails and is silently skipped rather than leaving a scheduled,
# unattended job to sort out a conflict on its own.
function _pull_main_if_clean() {
  local repo="$1"
  local default_branch current_branch before after
  default_branch=$(git -C "$repo" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
  [[ -n "$default_branch" ]] || return 0
  current_branch=$(git -C "$repo" branch --show-current 2>/dev/null)
  [[ "$current_branch" == "$default_branch" ]] || return 0

  before=$(git -C "$repo" rev-parse HEAD 2>/dev/null)
  git -C "$repo" fetch --quiet origin "$default_branch" 2>/dev/null
  if git -C "$repo" merge --ff-only --quiet "origin/$default_branch" 2>/dev/null; then
    after=$(git -C "$repo" rev-parse HEAD 2>/dev/null)
    [[ "$before" != "$after" ]] && echo "  ⬆ Updated $default_branch: ${before:0:7} → ${after:0:7}"
  fi
}

# Cross-repo repo hygiene: keeps each repo's main branch current and prunes stale
# worktrees, across every repo under $HOME (2 levels deep, to also catch nested
# repos like pscloudops/terraform-infrastructure) that has a .worktrees directory
# at all -- both are things `gpr` already does for whichever single repo you
# happen to run it in, but a repo you haven't touched with `gpr` in a while just
# drifts behind origin and keeps accumulating stale MERGED/CLOSED worktrees.
function gprune() {
  local -a repos=("$HOME"/*/.worktrees(N) "$HOME"/*/*/.worktrees(N))
  repos=("${repos[@]%/.worktrees}")

  if [[ ${#repos[@]} -eq 0 ]]; then
    echo "gprune: no repos with .worktrees found under $HOME"
    return 0
  fi

  local repo
  for repo in "${repos[@]}"; do
    # A stray .worktrees dir with no .git alongside it isn't a repo at all (seen in
    # practice: an empty leftover ~/pscloudops/.worktrees where pscloudops is just a
    # container folder for nested repos, not a repo itself) -- skip it rather than
    # letting git's "not a git repository" error leak into the output below.
    [[ -d "$repo/.git" || -f "$repo/.git" ]] || continue
    echo "═══ ${repo#$HOME/} ═══"
    _pull_main_if_clean "$repo"
    _gpr_prune_stale_worktrees "$repo"
  done
}

# Standalone version of the "Updating tracked repositories to latest main..."
# step that darwin-rebuild switch already runs on every activation (see
# nix-modules/macos/config.nix) -- lets you pull the same repos without a full
# rebuild. Ported verbatim from that activation script's bash, so behavior
# matches exactly: stashes dirty state, switches to main/master if needed,
# pulls + updates submodules, switches back, pops the stash. Repos are
# discovered dynamically (anything directly under $HOME with a .git entry),
# same as config.nix -- a newly cloned repo is picked up automatically by
# both, nothing to edit here.
function update-repos() {
  local -a tracked_repos=("$HOME"/*/.git(N))
  tracked_repos=("${tracked_repos[@]%/.git}")

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
      git -C "$repo_path" stash push -m "update-repos auto-stash $(date +%Y%m%d-%H%M%S)" \
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
      && git -C "$repo_path" submodule update --init --recursive \
      || echo "  Warning: pull failed for $repo_name (SSH agent may not be available)."

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
  local tracked_repo
  for tracked_repo in "${tracked_repos[@]}"; do
    _update_repo_main "$tracked_repo"
  done
  unset -f _update_repo_main
  echo "Finished updating repositories."
}

