# Prints the owner/name of the GitHub repo that `origin` points at, or nothing when
# origin is not a GitHub URL (a local path, another host). Reads the raw configured URL,
# not `git remote get-url`, so an insteadOf rewrite cannot hide the GitHub identity.
# gh must be told this repo explicitly: in a fork clone gh resolves its default repo to the
# upstream parent (`gh repo fork` makes `upstream` the base), and a bare `gh pr create`
# would then open the PR against the parent instead of the fork.
function _gpr_origin_repo() {
  local url
  url=$(git -C "${1:-.}" config --get remote.origin.url 2>/dev/null) || return 1
  url=${url%.git}
  case "$url" in
    git@github.com:*|ssh://git@github.com/*|https://github.com/*|http://github.com/*) ;;
    *) return 1 ;;
  esac
  url=${url#git@github.com:}
  url=${url#*://}
  url=${url#git@}
  url=${url#github.com/}
  [[ "$url" == */* ]] && echo "$url"
}

# Prints the default branch of this repo's own `origin`, ignoring any `upstream` remote.
# Order: origin/HEAD (set at clone), then GitHub's answer for origin's own owner/name,
# then a local main or master. Prints nothing when none of them exists.
function _gpr_default_branch() {
  local repo="$1" branch slug b
  branch=$(git -C "$repo" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)
  branch=${branch#origin/}
  if [[ -z "$branch" ]] && slug=$(_gpr_origin_repo "$repo"); then
    branch=$(gh repo view "$slug" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null)
  fi
  if [[ -z "$branch" ]]; then
    for b in main master; do
      if git -C "$repo" rev-parse --verify --quiet "refs/heads/$b" >/dev/null; then
        branch=$b
        break
      fi
    done
  fi
  [[ -n "$branch" ]] && echo "$branch"
  return 0
}

# Worktree + PR hygiene: run before creating a new worktree so we don't
# accumulate stale checkouts, and so whoever is about to start new work can
# see what's already in flight first. $2, when given, is origin's owner/name: the PR
# lookups then target that repo, never the upstream parent of a fork.
#   - A worktree whose PR is MERGED/CLOSED is stale (the work is done or
#     dead) -> automatically removed, its local branch deleted.
#   - A worktree with an OPEN PR, or no PR at all (not pushed yet), is left
#     alone and just listed.
#   - An OPEN PR with no matching local worktree is only reported (it may
#     be in progress on another machine) -- never deleted.
function _gpr_prune_stale_worktrees() {
  local repo_root="$1"
  local pruned_any=false
  local -a open_worktree_branches=()
  local -a gh_repo=()
  [[ -n "${2:-}" ]] && gh_repo=(--repo "$2")

  echo "ℹ Checking existing worktrees and PRs..."

  local wt_path="" wt_branch=""
  while IFS= read -r line; do
    case "$line" in
      "worktree "*) wt_path="${line#worktree }" ;;
      "branch refs/heads/"*) wt_branch="${line#branch refs/heads/}" ;;
      "")
        if [[ -n "$wt_path" && "$wt_path" != "$repo_root" ]]; then
          if [[ -z "$wt_branch" ]]; then
            echo "  ⚠ Worktree with no branch (detached?): $wt_path — left alone"
          else
            # Explicit "" assignments avoid a zsh quirk: re-declaring an
            # already-local var with no assignment (as happens each loop
            # iteration here) prints "name=value" instead of no-op'ing.
            local pr_json="" pr_state=""
            if [[ ${#gh_repo[@]} -gt 0 ]]; then
              pr_json=$(cd "$wt_path" && gh pr view "${gh_repo[@]}" "$wt_branch" --json state,url 2>/dev/null)
            else
              pr_json=$(cd "$wt_path" && gh pr view --json state,url 2>/dev/null)
            fi
            if [[ -n "$pr_json" ]]; then
              pr_state=$(echo "$pr_json" | jq -r '.state')
              if [[ "$pr_state" == "MERGED" || "$pr_state" == "CLOSED" ]]; then
                echo "  🧹 Pruning stale worktree '$wt_branch' (PR $pr_state): $wt_path"
                git -C "$repo_root" worktree remove "$wt_path" --force 2>/dev/null
                git -C "$repo_root" branch -D "$wt_branch" 2>/dev/null
                pruned_any=true
              else
                local pr_url=$(echo "$pr_json" | jq -r '.url')
                echo "  • Active: '$wt_branch' — $pr_url"
                open_worktree_branches+=("$wt_branch")
              fi
            else
              echo "  • In progress (no PR yet): '$wt_branch' — $wt_path"
              open_worktree_branches+=("$wt_branch")
            fi
          fi
        fi
        wt_path="" wt_branch=""
        ;;
    esac
  done < <(git -C "$repo_root" worktree list --porcelain; echo)

  $pruned_any && git -C "$repo_root" worktree prune

  # Report open PRs with no local worktree — informational only, never touched.
  local open_prs
  open_prs=$(cd "$repo_root" && gh pr list "${gh_repo[@]}" --state open --json headRefName,url 2>/dev/null)
  if [[ -n "$open_prs" ]]; then
    echo "$open_prs" | jq -c '.[]' | while IFS= read -r pr; do
      local head_ref=$(echo "$pr" | jq -r '.headRefName')
      local pr_url=$(echo "$pr" | jq -r '.url')
      if [[ ! " ${open_worktree_branches[*]} " == *" $head_ref "* ]]; then
        echo "  ⓘ Open PR with no local worktree (maybe in progress elsewhere): $head_ref — $pr_url"
      fi
    done
  fi
  echo ""
}

