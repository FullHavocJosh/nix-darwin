# Strips Aider's own chrome (version/model/repo banner, the trailing
# "Tokens: N sent, M received." line), a leaked <think>...</think> block, and
# a markdown code fence wrapping the answer -- GLM in particular wraps JSON
# responses in ```json ... ```, the same fence-stripping gpc/gpa's old
# direct-curl path already needed.
#
# The <think> strip is needed despite model-settings.yml's
# chat_template_kwargs.enable_thinking=false: on the currently loaded model
# (GLM-4.7-Flash via llama-server --reasoning-format none) that setting does
# not stop the block from appearing in the response content -- only removing
# it from a separate reasoning_content field would, and this server config
# doesn't split it out. Verified live: every local-coder-plan/-judge call so
# far has emitted one. The second rule (no closing tag) covers a thinking
# block truncated by max_tokens before it could close -- nothing after an
# unclosed <think> is a usable answer either.
function _aider_extract_response() {
  perl -0777 -pe '
    s/^Warning:.*\n//mg;
    s/^You can skip this check.*\n//mg;
    s/^https:\/\/aider\.chat.*\n//mg;
    s/^Aider v.*\n//mg;
    s/^Model: .*\n//mg;
    s/^Git repo:.*\n//mg;
    s/^Repo-map:.*\n//mg;
    s/^Added .* to the chat.*\n//mg;
    s/^Tokens: .* sent, .* received\.\s*\n?//mg;
    s/<think>.*?<\/think>\s*//is;
    s/<think>.*$//is;
    s/^\s*```(?:json)?\s*\n//;
    s/\n?```\s*$//;
    s/^\s+//;
    s/\s+$//;
  '
}

# Runs a one-shot, read-only (--chat-mode ask, no file attached, no git
# operations) Aider query against this host's llama-server and prints the
# model's cleaned text response. The prompt is passed as the message body,
# not a --read file, matching how gpc/gpa already embed the diff directly in
# the prompt text rather than pointing at a file on disk.
#
# Timeouts for the local model, in seconds. Override per shell with AI_LOCAL_COMMIT_TIMEOUT / AI_LOCAL_REVIEW_TIMEOUT.
# A call has to cover the model's JIT load when it is not loaded (8-13s measured for the 9B, 22s for the 27B), prompt
# processing, and then generation, which dominates: measured generation speed of qwen3.5-9b is 10.6 tok/s on the
# MacMiniM1 and 22.5 tok/s on the MacBookM2Pro (prefill 72 and 156 tok/s). So a commit message (max_tokens 512,
# ~1.5k-token prompt) can take ~90s on the slowest host, and a review (max_tokens 4096, ~1k-token prompt) ~430s when
# the model uses its whole budget. The old 60s / 180s / 240s limits cut those off, and gpc/gpa then fail with
# "timeout" even though the model was working. The defaults leave about 3x headroom for the commit and 2x for the
# review; a hung model is still bounded.
function _local_llm_timeout() {
  case "$1" in
    commit) echo "${AI_LOCAL_COMMIT_TIMEOUT:-300}" ;;
    review) echo "${AI_LOCAL_REVIEW_TIMEOUT:-900}" ;;
    *)      echo "${AI_LOCAL_REVIEW_TIMEOUT:-900}" ;;
  esac
}

# Usage: _run_aider_local <model-alias> <timeout-seconds> <prompt>
# Returns: 0 on success (stdout = cleaned response), 1 on failure (stderr =
# error message matching the same "timeout"/"not reachable" wording the old
# direct-curl branches used, since gpc/gpa's own retry loop greps for those).
function _run_aider_local() {
  local model_alias="$1"
  local timeout_secs="$2"
  local prompt="$3"
  local endpoint="${LLAMA_CPP_HOST:-http://127.0.0.1:8080}"
  local settings_file aider_model tmp_settings

  if ! command -v aider &>/dev/null; then
    echo "Error: aider not installed" >&2
    return 1
  fi

  # llama-server serves one model under the alias LOCAL_LLM_MODEL (set in
  # llamacpp-local.nix), so aider is pointed at that and gets a one-entry
  # settings file carrying a per-purpose max_tokens (the alias only picks the cap).
  # chat_template_kwargs.enable_thinking=false goes in extra_body: Qwen3.5 reasons
  # by default and spends max_tokens on it, returning empty content. Verified on
  # llama-server 9190: that kwarg turns thinking off (2 tokens for "ok"), while
  # reasoning_effort "none" is ignored. Only aider (one-shot commit/review/judge
  # calls) disables reasoning; aistack tier 1 (pi, a live session) keeps it.
  local lms_model="${LOCAL_LLM_MODEL:-qwen/qwen3.5-9b}"
  local lms_max_tokens
  case "$model_alias" in
    local-coder-commit) lms_max_tokens=512 ;;   # one 72-char line; measured ~15-40 tokens
    local-coder-plan)   lms_max_tokens=1024 ;;
    local-coder-judge)  lms_max_tokens=256 ;;
    local-coder-secrets) lms_max_tokens=1536 ;;   # gpa's secrets analysis: a short verdict, but longer than a commit message
    local-coder-review) lms_max_tokens=3072 ;;  # JSON array capped at 10 issues (~1k tokens)
    *)                  lms_max_tokens=4096 ;;
  esac
  # Output cap never above 1/8 of the device's context window (the prompt needs the rest). The per-purpose caps
  # above fit every profile class today (smallest window 32768 -> 4096), so this only bites if a profile shrinks.
  if _llamacpp_profile_load && (( lms_max_tokens > LLAMA_CTX_SIZE / 8 )); then
    lms_max_tokens=$(( LLAMA_CTX_SIZE / 8 ))
  fi
  # Review, judge and secrets calls decide whether a commit goes through, so their sampling is pinned: the same
  # prompt gives the same findings instead of a new set on every run. Commit messages and plans keep the defaults.
  local lms_temperature="" lms_seed=""
  case "$model_alias" in
    local-coder-review|local-coder-judge|local-coder-secrets)
      lms_temperature=$'\n    temperature: 0'
      lms_seed=$'\n      seed: 20261008'
      ;;
  esac
  tmp_settings=$(mktemp "${TMPDIR:-/tmp}/aider-llama-settings.XXXXXX") || {
    echo "Error: could not create aider settings file" >&2
    return 1
  }
  cat > "$tmp_settings" <<EOF
- name: openai/${lms_model}
  edit_format: ask
  extra_params:
    max_tokens: ${lms_max_tokens}${lms_temperature}
    extra_body:${lms_seed}
      chat_template_kwargs:
        enable_thinking: false
EOF
  settings_file="$tmp_settings"
  aider_model="openai/${lms_model}"

  local raw_output
  # BROWSER=true: with --yes-always aider auto-accepts its "Open URL for more info?" offer when a call
  # hits a token limit and would open aider.chat/docs/troubleshooting/token-limits.html in a browser.
  # Python's webbrowser honors $BROWSER, so the page is "opened" with /usr/bin/true instead.
  raw_output=$(BROWSER=true timeout "${timeout_secs}s" aider \
    --model "$aider_model" \
    --openai-api-base "${endpoint}/v1" \
    --openai-api-key "sk-local" \
    --model-settings-file "$settings_file" \
    --no-git \
    --yes-always \
    --chat-mode ask \
    --no-pretty \
    --no-check-update \
    --no-analytics \
    --no-show-model-warnings \
    --no-detect-urls \
    --input-history-file /tmp/.aider-local-input-history \
    --chat-history-file /tmp/.aider-local-chat-history.md \
    --message "$prompt" 2>&1)
  local exit_code=$?
  [[ -n "$tmp_settings" ]] && rm -f "$tmp_settings"

  if [ $exit_code -eq 124 ]; then
    echo "Error: local model timeout after ${timeout_secs}s (raise AI_LOCAL_COMMIT_TIMEOUT or AI_LOCAL_REVIEW_TIMEOUT)" >&2
    return 1
  elif [ $exit_code -ne 0 ]; then
    if echo "$raw_output" | grep -qi "connection\|connect\|refused"; then
      echo "Error: llama-server not reachable (run: sudo launchctl kickstart -k system/org.nixos.llama-server-local)" >&2
    else
      echo "Error: aider failed (exit code: $exit_code): $raw_output" >&2
    fi
    return 1
  fi

  # Aider prints this and exits 0 when finish_reason is "length". What is left is a truncated answer (a
  # cut-off review/commit message) plus aider's error text, which must not be used as the model's reply.
  # (anchored at line start so a review that merely quotes the phrase does not trigger it)
  if echo "$raw_output" | grep -Eq "^Model [^ ]+ has hit a token limit!"; then
    echo "Error: local model hit its token limit (alias $model_alias, max_tokens ${lms_max_tokens}) -- output was truncated and was discarded" >&2
    return 1
  fi

  local extracted=$(echo "$raw_output" | _aider_extract_response)
  if [[ -n "$extracted" ]]; then
    echo "$extracted"
    return 0
  fi

  echo "Error: aider returned empty response" >&2
  return 1
}

