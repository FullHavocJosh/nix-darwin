# Git PR - Create new branch, worktree, and draft pull request.
#
# Development happens in a worktree per PR (~/.worktrees/<branch> inside the
# repo), not by checking out a branch in place -- the main repo checkout
# always stays on main so concurrent work-in-progress branches don't collide
# in a single working directory.
# gpr's interface for AI callers (aistack, aidev, Claude Code, opencode, pi):
#   gpr --auto <feat|fix> <branch> --title "<PR title>" --description "<PR body, markdown>"
#   --auto        never prompts (a missing type or branch is an error) and implies --json
#   --title       the draft PR's title and the first commit's subject (default "<type>: <branch>")
#   --description the PR body (or --body-file <path>); default is the short template
#   --json        stdout is ONE line of JSON, the human log goes to stderr:
#                 {"ok":true,"branch","worktree","pr_url","pr_number","title"} or {"ok":false,"error"}
# Without these flags gpr behaves exactly as before. The worktree is NOT entered (see _gpr_impl).
function gpr_func() {
  local title="" body="" auto=0 json=0
  local -a pos
  while (( $# )); do
    case "$1" in
      --auto) auto=1; json=1; shift ;;
      --json) json=1; shift ;;
      --title) title="$2"; shift 2 ;;
      --description|--body) body="$2"; shift 2 ;;
      --body-file) body="$(<"$2")" || return 2; shift 2 ;;
      -*) echo "✗ gpr: unknown option $1 (usage: gpr [--auto] [--json] [--title T] [--description D] <feat|fix> <branch>)" >&2; return 2 ;;
      *) pos+=("$1"); shift ;;
    esac
  done
  # A title or body left empty falls back to gpr's default title or template body.
  title=$(_strip_agent_attribution "$title")
  body=$(_strip_agent_attribution "$body")
  local result_file
  result_file=$(mktemp)
  local -x GPR_TITLE="$title" GPR_BODY="$body" GPR_RESULT_FILE="$result_file" GPR_AUTO="${auto:#0}"
  if (( ! json )); then
    _gpr_impl "${pos[@]}"
    local rc=$?
    rm -f "$result_file"
    return $rc
  fi
  local logf rc
  logf=$(mktemp)
  _gpr_impl "${pos[@]}" > "$logf" 2>&1
  rc=$?
  cat "$logf" >&2
  if [[ -s "$result_file" ]]; then
    jq -c --arg title "${title:-}" '. + {ok: true} + (if $title == "" then {} else {title: $title} end)' "$result_file"
    rc=0
  else
    jq -nc --arg err "$(sed $'s/\x1b\\[[0-9;]*m//g' "$logf" | grep -E '^(✗|fatal|error)' | tail -1)" \
      --arg tail "$(sed $'s/\x1b\\[[0-9;]*m//g' "$logf" | tail -5)" '{ok: false, error: (if $err == "" then "gpr failed" else $err end), output_tail: $tail}'
    [[ $rc -eq 0 ]] && rc=1
  fi
  rm -f "$logf" "$result_file"
  return $rc
}

function _gpr_impl() {
  # Usage: gpr [feat|fix] [branch-name]
  # Positional args skip the interactive prompts below (for scripted/AI callers).
  # GPR_TITLE / GPR_BODY (set by gpr_func from --title / --description) replace the default PR title and body;
  # GPR_AUTO makes a missing type or branch an error instead of a prompt; GPR_RESULT_FILE receives the result JSON.
  local arg_type="$1"
  local arg_branch_name="$2"

  # Validate git repository
  _check_git_repo || return 1

  local repo_root
  repo_root=$(git rev-parse --show-toplevel)

  if ! _is_main_worktree "$repo_root"; then
    local common_dir main_root
    common_dir=$(git rev-parse --path-format=absolute --git-common-dir)
    main_root=$(cd "$(dirname "$common_dir")" && pwd)
    echo "✗ You're inside a worktree. Run gpr from the main repo checkout instead:"
    echo "  cd $main_root"
    return 1
  fi

  # The repo's own origin and default branch, never those of an upstream parent: in a
  # fork clone gh's default repo is the parent, and the fork's default branch need not be main.
  local origin_repo base_branch
  origin_repo=$(_gpr_origin_repo "$repo_root")
  base_branch=$(_gpr_default_branch "$repo_root")
  if [[ -z "$base_branch" ]]; then
    echo "✗ Cannot find origin's default branch (origin/HEAD, GitHub, local main or master)"
    return 1
  fi

  # gpr never calls an AI provider — branch naming and PR creation are
  # templated operations that don't benefit from cloud quality.
  echo "🏠 Creating PR locally (no AI provider needed)..."
  echo "ℹ Base: ${origin_repo:-origin} @ $base_branch"
  echo ""

  _gpr_prune_stale_worktrees "$repo_root" "$origin_repo"

  # Stash any uncommitted changes
  echo "Stashing uncommitted changes..."
  local stash_result=$(git stash)
  local did_stash=false
  if [[ "$stash_result" != "No local changes to save" ]]; then
    did_stash=true
  fi

  # Always attempt git pull, continue regardless of result
  echo "Pulling latest changes..."
  git pull || true

  # Restore stashed changes only if we stashed something
  if [[ "$did_stash" == true ]]; then
    echo "Restoring stashed changes..."
    git stash pop || true
  fi

  local type_choice="$arg_type"
  if [ -z "$type_choice" ] && [ -n "${GPR_AUTO:-}" ]; then
    echo "✗ --auto needs a type: feat or fix"
    return 1
  fi
  if [ -z "$type_choice" ]; then
    echo "Select type:"
    echo "  1) feat"
    echo "  2) fix"
    echo -n "Enter choice (1 or 2): "
    read type_choice
  fi
  case "$type_choice" in
    1|feat) type_prefix="feat" ;;
    2|fix) type_prefix="fix" ;;
    *)
      echo "✗ Invalid choice. Please select 1, 2, feat, or fix"
      return 1
      ;;
  esac
  local branch_name="$arg_branch_name"
  if [ -z "$branch_name" ] && [ -n "${GPR_AUTO:-}" ]; then
    echo "✗ --auto needs a branch name"
    return 1
  fi
  if [ -z "$branch_name" ]; then
    echo -n "Branch name: "
    read branch_name
  fi
  if [ -z "$branch_name" ]; then
    echo "✗ Branch name cannot be empty"
    return 1
  fi

  local worktree_dir="$repo_root/.worktrees/$branch_name"
  if [ -e "$worktree_dir" ]; then
    echo "✗ A worktree already exists at $worktree_dir"
    return 1
  fi
  mkdir -p "$repo_root/.worktrees"

  git worktree add -b "$branch_name" "$worktree_dir" "$base_branch" || return 1

  # Deliberately NOT cd'ing the caller's shell into the worktree. aidev is often
  # working through a whole run of PRs/worktrees in one sitting (create worktree,
  # land the PR, move to the next), and if gpr moved it each time it'd lose track
  # of "home base" -- the repo root, or wherever devim was originally triggered
  # from -- a little more with every worktree. Everything below that needs to run
  # inside the worktree does so in a subshell instead, so this shell's own cwd
  # never changes; $worktree_dir is reported at the end for anything that
  # genuinely needs to work IN it afterward.
  local pr_title="${GPR_TITLE:-$type_prefix: $branch_name}"
  local pr_body="${GPR_BODY:-}"
  if [ -z "$pr_body" ]; then
    pr_body="## Description
$type_prefix: $branch_name

## Tickets
$type_prefix: $branch_name"
  fi
  local pr_url pr_rc
  # --repo/--base/--head pin the PR to origin's own repo and default branch; without them a fork
  # clone opens the PR against the upstream parent.
  local -a pr_target=(--base "$base_branch" --head "$branch_name")
  [[ -n "$origin_repo" ]] && pr_target=(--repo "$origin_repo" "${pr_target[@]}")
  pr_url=$(
    cd "$worktree_dir" || exit 1
    git commit --allow-empty -m "${GPR_TITLE:-$branch_name}" >&2 &&
      git push -u origin "$branch_name" >&2 &&
      gh pr create --draft "${pr_target[@]}" --title "$pr_title" --body "$pr_body"
  )
  pr_rc=$?
  [ -n "$pr_url" ] && echo "$pr_url"
  if [ $pr_rc -ne 0 ]; then
    echo "✗ Creating the branch or draft PR failed (worktree left at $worktree_dir)"
    return $pr_rc
  fi
  echo ""
  echo "✓ Worktree ready: $worktree_dir"
  if [ -n "${GPR_RESULT_FILE:-}" ]; then
    jq -nc --arg branch "$branch_name" --arg worktree "$worktree_dir" --arg url "$pr_url" \
      '{branch: $branch, worktree: $worktree, pr_url: $url, pr_number: (($url | capture("/pull/(?<n>[0-9]+)") | .n | tonumber)? // null)}' \
      > "$GPR_RESULT_FILE"
  fi

  # aidev's own pane deliberately stays put (see above), but the sibling
  # nvim/zsh panes over in the workspace's dev tab should still follow the
  # worktree -- that's where the actual file changes are happening, so they
  # should be showing it even though aidev's cwd doesn't move. Push them there
  # when running in tuios.
  [ -n "$TUIOS_ENV" ] && _tuios_sync_dev_panes "$worktree_dir"
  return 0
}
