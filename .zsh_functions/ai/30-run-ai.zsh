# Plain-text call to the local model (commit messages, gpa's secrets analysis). gpa/gpc/gpr only ever run on
# llama.cpp through aider; the one cloud path is gpa's escalation to Claude Code (_run_ai_direct_claude).
# Usage: echo "prompt" | _run_ai_plain
function _run_ai_plain() {
  local prompt=$(cat)

  # Truncate prompt to ~6000 chars to keep it fast for plain-text tasks
  # (commit messages only need a representative sample of the diff)
  local truncated_prompt="${prompt:0:6000}"
  local prompt_len=${#prompt}
  if [ $prompt_len -gt 6000 ]; then
    truncated_prompt="${truncated_prompt}
... [diff truncated at 6000 chars for speed — ${prompt_len} total]"
  fi

  # Routed through Aider instead of a direct curl call -- Aider handles
  # response extraction robustly (its own --chat-mode ask flow), so this
  # replaces what used to be a hand-rolled curl+jq+perl chain here (raw
  # newline JSON parsing, <think> block stripping, markdown fence
  # stripping all lived in this branch and each had its own real bug
  # fixed earlier). The chat_template_kwargs.enable_thinking=false fix is
  # preserved via .config/aider/model-settings.yml's openai/local-coder-commit
  # entry instead of being inlined in the request body here.
  _run_aider_local "${AI_LOCAL_ALIAS:-local-coder-commit}" "$(_local_llm_timeout commit)" "$truncated_prompt"
}

# Structured call to the local model that prints a JSON array (gpa's review and its second look at a finding).
# Exit codes: 0 = valid JSON array, 1 = hard failure (timeout, server down), 2 = reply not parseable ("[]" printed).
# Usage: echo "prompt" | _run_ai_direct
function _run_ai_direct() {
  local prompt=$(cat)

  # Cap the prompt to keep prompt processing reasonable, but keep BOTH ends: the review prompt ends
  # with the instructions ("Output ONLY a JSON array ...", the issue limit), so a plain prefix cut dropped
  # them and the model answered with an unbounded markdown review that ran into max_tokens (seen twice
  # on 2026-10-06, ~3.8k output tokens, cut off mid-sentence). The middle of the diff is what gets omitted.
  # (Output max_tokens comes from _run_aider_local's per-alias cap.)
  local max_chars=6000 tail_chars=2400
  local truncated_prompt="$prompt"
  local prompt_len=${#prompt}
  if [ $prompt_len -gt $max_chars ]; then
    truncated_prompt="${prompt:0:$((max_chars - tail_chars))}
... [diff middle omitted: ${prompt_len} chars total, first $((max_chars - tail_chars)) and last ${tail_chars} kept] ...
${prompt: -$tail_chars}"
  fi

  # The limit comes from _local_llm_timeout (900s by default; see the measurements there): a review that uses its
  # whole 4096-token output budget needs ~430s at the 9B's slowest measured generation speed.
  local aider_output
  aider_output=$(_run_aider_local "local-coder-review" "$(_local_llm_timeout review)" "$truncated_prompt")
  local aider_exit=$?
  if [ $aider_exit -ne 0 ]; then
    echo "$aider_output" >&2
    return 1
  fi

  # _run_aider_local already stripped Aider's own chrome and any markdown fence, but the array-extraction regex
  # stays as a safety net in case the model wraps the array in stray prose.
  if [[ -z "${aider_output//[[:space:]]/}" ]]; then
    echo "Error: Aider returned empty response" >&2
    echo "[]"
    return 2
  fi
  # Error response (first non-empty line starts with "Error:") is a hard
  # failure: never run jq on it, never emit "[]" as if it were valid.
  if echo "$aider_output" | grep -m1 -v '^[[:space:]]*$' | grep -q '^Error:'; then
    echo "Error: Aider returned an error response: $(echo "$aider_output" | head -c 200)" >&2
    return 1
  fi

  local json_extracted=$(echo "$aider_output" | perl -0777 -pe 's/.*(\[.*?\])\s*$/$1/s' | head -c 50000)
  if [[ -n "${json_extracted//[[:space:]]/}" ]] && echo "$json_extracted" | jq empty 2>/dev/null; then
    echo "$json_extracted"
    return 0
  fi

  # Soft failure: response not parseable as JSON
  echo "Error: Could not parse aider response as JSON" >&2
  echo "[]"
  return 2
}

# Tier 0 probe: prints "lumo" when a lumo-tamer answers /v1/models with its key, otherwise "local". Tried in order:
# this machine's own tamer (127.0.0.1:3003, key from ~/lumo-tamer-fullhavoc/config.yaml), MacMiniM1's on the home network (key
# from Doppler), then the public endpoint https://lumo.rollet.family/v1 (key from Doppler root_hetzner-cluster, or
# AISTACK_LUMO_PUBLIC_KEY). Each is tried only when the one before does not answer. aidev_lib.py uses the same order for
# the requests themselves. AISTACK_TIER0=local forces local; AISTACK_TAMER_URL / AISTACK_TAMER_KEY pin one endpoint.
function _aistack_tier0() {
  [[ "${AISTACK_TIER0:-auto}" == "local" ]] && { echo local; return 0; }
  local url key
  _aistack_tamer_ok() {   # url, key -> 0 when /models answers 200
    local -a auth
    [[ -n "$2" ]] && auth=(-H "Authorization: Bearer $2")
    [[ "$(curl -s -m 4 -o /dev/null -w '%{http_code}' "${auth[@]}" "${1%/}/models" 2>/dev/null)" == "200" ]]
  }
  url="${AISTACK_TAMER_URL:-${AISTACK_LUMO_URL:-}}"     # AISTACK_LUMO_URL / _KEY: the older names for the same pin
  if [[ -n "$url" ]]; then
    _aistack_tamer_ok "$url" "${AISTACK_TAMER_KEY:-${AISTACK_LUMO_KEY:-}}" && echo lumo || echo local
    return 0
  fi
  key=$(sed -n 's/^ *apiKey: *"\(.*\)" *$/\1/p' "$HOME/lumo-tamer-fullhavoc/config.yaml" 2>/dev/null | head -1)
  _aistack_tamer_ok "http://127.0.0.1:3003/v1" "$key" && { echo lumo; return 0; }
  key="${AISTACK_TAMER_MINI_KEY:-}"
  if [[ -z "$key" ]] && command -v doppler >/dev/null; then
    key=$(doppler secrets get LUMO_TAMER_API_KEY --project FullHavocJosh --config root_macmini --plain 2>/dev/null)
  fi
  _aistack_tamer_ok "${AISTACK_TAMER_MINI_URL:-http://macminim1.rollet.family:3003/v1}" "$key" && { echo lumo; return 0; }
  key="${AISTACK_LUMO_PUBLIC_KEY:-}"
  if [[ -z "$key" ]] && command -v doppler >/dev/null; then
    key=$(doppler secrets get LUMO_PUBLIC_API_KEY --project FullHavocJosh --config root_hetzner-cluster --plain 2>/dev/null)
  fi
  if [[ -n "$key" ]]; then
    _aistack_tamer_ok "${AISTACK_LUMO_PUBLIC_URL:-https://lumo.rollet.family/v1}" "$key" && { echo lumo; return 0; }
  fi
  echo local
}



# Validation Functions for AI Providers

