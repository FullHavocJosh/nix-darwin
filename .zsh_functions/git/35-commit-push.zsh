# Commit the staged changes with a message the caller already wrote, then push. $1 = subject, $2 = optional body.
# Shared by `gpc -m`, `gpa -m` (which ends in gpc) and anything else that supplies its own message, so no AI
# provider is involved and nothing can prompt.
function _gpc_commit_push() {
  local subject body
  subject=$(_strip_agent_attribution "$1")
  body=$(_strip_agent_attribution "$2")
  if [[ -z "$subject" ]]; then
    echo "✗ Commit subject was only agent attribution; nothing left to commit with" >&2
    return 1
  fi
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  $subject"
  echo "═══════════════════════════════════════════════════════════"
  echo ""
  if [[ -n "$body" ]]; then
    git commit -m "$subject" -m "$body"
  else
    git commit -m "$subject"
  fi
  if [ $? -ne 0 ]; then
    echo "✗ Commit failed, skipping push"
    return 1
  fi
  echo ""
  echo "ℹ Pushing to $(git remote get-url origin 2>/dev/null || echo remote)..."
  if git push; then
    echo "✓ Successfully pushed"
  else
    echo "✗ Push failed"
    return 1
  fi
}

