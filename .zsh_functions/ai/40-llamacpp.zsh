# Device profile (RAM class, context, KV cache types): ~/.config/llama/profile.sh, the same file the llama-server
# launcher embeds, so the shell and the server agree. Sets LLAMA_RAM_GB, LLAMA_CLASS, LLAMA_CTX_SIZE, LLAMA_KV_K/V.
function _llamacpp_profile_load() {
  local f="${LLAMA_PROFILE_FILE:-$HOME/.config/llama/profile.sh}"
  [[ -r "$f" ]] || return 1
  source "$f" && llama_profile
}

function _llamacpp_model_tier() {
  if _llamacpp_profile_load; then
    echo "${LOCAL_LLM_MODEL:-qwen/qwen3.5-9b} (llama.cpp, ${LLAMA_RAM_GB} GB device, ${LLAMA_CLASS} profile)"
  else
    echo "${LOCAL_LLM_MODEL:-qwen/qwen3.5-9b} (llama.cpp)"
  fi
}

# llamacpp_profile: what the device profile says versus what the running llama-server was started with.
# A mismatch means the server predates the profile: run darwin-rebuild switch (it restarts the launchd job).
function llamacpp_profile() {
  _llamacpp_profile_load || { echo "✗ ~/.config/llama/profile.sh is missing -- run darwin-rebuild so it is stowed." >&2; return 1; }
  local endpoint="${LLAMA_CPP_HOST:-http://127.0.0.1:8080}" args run_ctx run_k run_v
  echo "Device:   ${LLAMA_RAM_GB} GB -> ${LLAMA_CLASS}"
  echo "Profile:  ctx=${LLAMA_CTX_SIZE} kv=${LLAMA_KV_K}/${LLAMA_KV_V}"
  args=$(ps -axo command | grep '[l]lama-server --model' | head -1)
  if [[ -z "$args" ]]; then echo "Running:  no llama-server process"; return 0; fi
  run_ctx=$(sed -n 's/.*--ctx-size \([0-9]*\).*/\1/p' <<<"$args")
  run_k=$(sed -n 's/.*--cache-type-k \([a-z0-9_]*\).*/\1/p' <<<"$args")
  run_v=$(sed -n 's/.*--cache-type-v \([a-z0-9_]*\).*/\1/p' <<<"$args")
  echo "Running:  ctx=${run_ctx:-?} kv=${run_k:-?}/${run_v:-?} ($endpoint)"
  if [[ "$run_ctx" == "$LLAMA_CTX_SIZE" && "$run_k" == "$LLAMA_KV_K" && "$run_v" == "$LLAMA_KV_V" ]]; then
    echo "✓ running server matches the profile"
  else
    echo "⚠ running server differs from the profile: darwin-rebuild switch restarts it with the profile"
  fi
}


# Name kept for the callers; the local model is now whatever LOCAL_LLM_MODEL
# names (set in llamacpp-local.nix).
function _llamacpp_model_short() {
  echo "${LOCAL_LLM_MODEL:-qwen/qwen3.5-9b}"
}


function _validate_llamacpp() {
  local endpoint="${LLAMA_CPP_HOST:-http://127.0.0.1:8080}"
  local lms_model="${LOCAL_LLM_MODEL:-qwen/qwen3.5-9b}"
  # Local AI only ever talks to llama-server on this machine's loopback. Reject
  # any other host (a stray LLAMA_CPP_HOST pointing at another device, a LAN
  # address, a hostname) before sending a prompt anywhere.
  case "$endpoint" in
    http://127.0.0.1:*|http://localhost:*|http://\[::1\]:*) ;;
    *) return 1 ;;
  esac
  # llama-server answers /v1/models with its --alias; it only lists the model
  # once it is loaded and ready.
  curl -s --max-time 3 "${endpoint}/v1/models" 2>/dev/null | grep -q "\"${lms_model}\""
}

