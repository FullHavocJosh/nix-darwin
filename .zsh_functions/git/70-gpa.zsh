# Helper function: Prompt user for action on AI errors
# Usage: _prompt_ai_error_action <error_message> <context>
# Returns: 0 for retry, 1 for continue, 2 for cancel
function _prompt_ai_error_action() {
  local error_msg="$1"
  local context="${2:-AI operation}"
  
  echo "" >&2
  echo "⚠ ERROR: $error_msg" >&2
  echo "  Context: $context" >&2
  echo "" >&2
  echo "Options:" >&2
  echo "  [Enter] Retry" >&2
  echo "  [i]     Ignore and continue" >&2
  echo "  [esc]   Cancel" >&2
  echo "" >&2
  echo -n "Your choice: " >&2
  
  # Read a single character
  local choice
  read -r choice
  
  case "$choice" in
    ""|$'\n')  # ENTER key
      return 0  # Retry
      ;;
      i|I)
      return 1  # Ignore
      ;;
    $'\e'|q|Q)  # ESC or q
      return 2  # Cancel
      ;;
    *)
      # Invalid input, treat as cancel
      echo "⚠ Invalid input, cancelling..." >&2
      return 2
      ;;
  esac
}

# gpa's interface for AI callers (aistack, aidev, Claude Code, opencode, pi). Everything else is _gpa_impl.
#   gpa --auto -m "<commit subject>" [-d "<commit body>"] [--no-review] [--json]
#   -m / -d     the commit message is yours: gpc does not generate one (AI_COMMIT_MESSAGE / AI_COMMIT_BODY)
#   --no-review skip the AI code review (secrets scan and linters still run); for callers that already reviewed
#   --json      stdout is ONE line of JSON, {"ok","exit_code","commit","subject","branch","pushed","output_tail"},
#               and the human log goes to stderr. Without it the output is the human text, as always.
# Exit code: 0 committed and pushed; non-zero with the findings printed (see _gpa_impl --auto).
function gpa() {
  local -a rest
  local msg="" body="" json=0 noreview="" waive="" reason=""
  while (( $# )); do
    case "$1" in
      --waive) waive="${waive:+$waive }$2"; shift 2 ;;
      --reason) reason="$2"; shift 2 ;;
      -m|--message) msg="$2"; shift 2 ;;
      -d|--description|--body) body="$2"; shift 2 ;;
      --json) json=1; shift ;;
      --no-review) noreview=1; shift ;;
      *) rest+=("$1"); shift ;;
    esac
  done
  local -x AI_COMMIT_MESSAGE="${msg:-${AI_COMMIT_MESSAGE:-}}" AI_COMMIT_BODY="${body:-${AI_COMMIT_BODY:-}}"
  # Strip before the review runs and before a Review-waived line is appended; gpc strips again as the backstop.
  if [[ -n "$AI_COMMIT_MESSAGE" ]]; then
    AI_COMMIT_MESSAGE=$(_strip_agent_attribution "$AI_COMMIT_MESSAGE")
    if [[ -z "$AI_COMMIT_MESSAGE" ]]; then
      echo "✗ Commit subject was only agent attribution; nothing left to commit with" >&2
      return 2
    fi
  fi
  AI_COMMIT_BODY=$(_strip_agent_attribution "$AI_COMMIT_BODY")
  local -x GPA_NO_REVIEW="${noreview:-${GPA_NO_REVIEW:-}}"
  # --waive <fingerprint> --reason "<why>": let one confirmed review finding through. The fingerprint is printed with
  # the finding. It is a person's decision, so it is refused together with --auto (the AI-agent interface), and it is
  # written into the commit message as a "Review-waived:" line, which is why it needs -m.
  local -x GPA_WAIVE="" GPA_WAIVE_REASON="" GPA_WAIVED_FILE=""
  if [[ -n "$waive" ]]; then
    if (( ${rest[(Ie)--auto]} )); then
      echo "✗ --waive is not available with --auto: a waiver is a person's decision. Report the finding to the user." >&2
      return 2
    fi
    if [[ -z "$reason" || -z "$msg" ]]; then
      echo "✗ --waive needs --reason \"<why>\" and -m \"<commit subject>\" (the waiver is recorded in the commit message)." >&2
      return 2
    fi
    GPA_WAIVE="$waive" GPA_WAIVE_REASON="$reason" GPA_WAIVED_FILE=$(mktemp)
  fi
  if (( ! json )); then
    _gpa_impl "${rest[@]}"
    return $?
  fi
  local logf rc head_before ok=false pushed=false
  logf=$(mktemp)
  head_before=$(git rev-parse HEAD 2>/dev/null)
  _gpa_impl "${rest[@]}" > "$logf" 2>&1
  rc=$?
  cat "$logf" >&2
  [[ $rc -eq 0 ]] && ok=true
  grep -q "Successfully pushed" "$logf" && pushed=true
  local commit="" subject=""
  if [[ "$(git rev-parse HEAD 2>/dev/null)" != "$head_before" ]]; then
    commit=$(git rev-parse HEAD 2>/dev/null)
    subject=$(git log -1 --format=%s 2>/dev/null)
  fi
  jq -nc --argjson ok "$ok" --argjson rc "$rc" --arg commit "$commit" --arg subject "$subject" \
    --arg branch "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" --argjson pushed "$pushed" \
    --arg tail "$(sed $'s/\x1b\\[[0-9;]*m//g' "$logf" | tail -40)" \
    '{ok: $ok, exit_code: $rc, commit: (if $commit == "" then null else $commit end), subject: $subject, branch: $branch, pushed: $pushed, output_tail: $tail}'
  rm -f "$logf"
  return $rc
}

# Local-only variant of gpa: the local-model-failed fallback and the critical-security-finding escalation to
# Claude Code are both suppressed -- a run either completes on-device or fails, never quietly switches to a billed
# model. An explicit --tier still asks Claude Code.
function gpa-local() {
  local _had_prev=0
  [[ -n "${AI_LOCAL_ONLY+x}" ]] && _had_prev=1
  local _prev="$AI_LOCAL_ONLY"
  export AI_LOCAL_ONLY=1
  gpa "$@"
  local ret=$?
  if [[ $_had_prev -eq 1 ]]; then
    export AI_LOCAL_ONLY="$_prev"
  else
    unset AI_LOCAL_ONLY
  fi
  return $ret
}


