function _ai_provider_enabled() {
  local name="$1"
  
  # Check if the environment variable is set
  local var_name="AI_${name}_ENABLED"
  if [[ -n "${(P)var_name}" ]]; then
    # If the env var is set to off, false, no, or 0 (case-insensitive), return 1 (disabled)
    case "${(P)var_name}" in
      [oO][fF][fF]|[fF][aA][lL][sS][eE]|[nN][oO]|[0O])
        return 1
        ;;
      *)
        return 0
        ;;
    esac
  fi
  
  # If env var is not set, check for .off file
  local switches_dir="${${AI_HOME/#\~/$HOME}:-$HOME/.ai}/switches"
  if [[ -f "${switches_dir}/${name}.off" ]]; then
    return 1  # Provider disabled by file
  fi
  
  # Default is enabled
  return 0
}

function _validate_claude_code() {
  _ai_provider_enabled claude || return 1
  command -v claude &>/dev/null || return 1
  # API key auth
  [[ -n "$ANTHROPIC_API_KEY" ]] && return 0
  # OAuth session - use `claude auth status` to check if logged in
  if claude auth status 2>/dev/null | grep -q '"loggedIn": true'; then
    return 0
  fi
  return 1
}

# gpa's one cloud path: a structured review call to Claude Code, used when the local review hard-fails, when it finds
# a Critical security issue and the user escalates, or when --tier names a model. Never runs under AI_LOCAL_ONLY
# (gpa-local, or plain gpa on hosts that set AI_LOCAL_DEFAULT): the callers check that. Billed, so it is small:
#   --tools ""                the diff is in the prompt; no file, shell or web tools
#   --setting-sources ""      no user/project settings, so no hooks, plugins or permission rules run here
#   --strict-mcp-config       no MCP servers
#   --json-schema             Claude Code validates the reply; the issues come back in .structured_output
#   --max-budget-usd          hard cap for the one call (GPA_CLAUDE_BUDGET_USD)
# Prints a JSON array with the same exit codes as _run_ai_direct: 0 ok, 1 hard failure, 2 unparseable ("[]" printed).
# Usage: echo "prompt" | _run_ai_direct_claude [haiku|sonnet|opus]
function _run_ai_direct_claude() {
  local model="${1:-sonnet}"
  local prompt=$(cat)
  if ! _validate_claude_code; then
    echo "Error: Claude Code is not logged in (run: claude auth login)" >&2
    return 1
  fi
  local schema='{"type":"object","required":["issues"],"properties":{"issues":{"type":"array","items":{"type":"object",
"required":["file","severity","issue","recommendation","category","evidence"],"properties":{"file":{"type":"string"},
"severity":{"type":"string","enum":["Critical","Warning"]},"issue":{"type":"string"},"recommendation":{"type":"string"},
"category":{"type":"string","enum":["secret-exposure","injection","destructive-command","broken-syntax","auth-bypass","other"]},
"evidence":{"type":"string"}}}}}}'
  local result exit_code errf
  errf=$(mktemp "${TMPDIR:-/tmp}/gpa-claude-err.XXXXXX") || return 1
  result=$(print -r -- "$prompt" | timeout "${GPA_CLAUDE_TIMEOUT:-180}s" claude -p --model "$model" --effort medium \
    --tools "" --setting-sources "" --strict-mcp-config --disable-slash-commands --no-session-persistence \
    --max-budget-usd "${GPA_CLAUDE_BUDGET_USD:-0.5}" --output-format json --json-schema "$schema" 2>"$errf")
  exit_code=$?
  local err_text=$(head -c 300 "$errf"); rm -f "$errf"
  if [ $exit_code -eq 124 ]; then
    echo "Error: Claude Code timeout after ${GPA_CLAUDE_TIMEOUT:-180}s" >&2
    return 1
  elif [ $exit_code -ne 0 ] || [[ "$(jq -r '.is_error' <<<"$result" 2>/dev/null)" != "false" ]]; then
    # (not `.is_error // true`: jq's // treats false as missing, so it would turn every success into a failure)
    echo "Error: Claude Code call failed (exit $exit_code): ${err_text:-$(print -r -- "$result" | head -c 200)}" >&2
    return 1
  fi
  local issues
  issues=$(jq -c '.structured_output.issues // empty' <<<"$result" 2>/dev/null)
  if [[ -n "$issues" ]] && jq -e 'type == "array"' <<<"$issues" >/dev/null 2>&1; then
    print -r -- "$issues"
    return 0
  fi
  echo "Error: Claude Code reply had no structured issues" >&2
  echo "[]"
  return 2
}

