# Review through the llm.rollet.family gateway (auto-review group: Cait G14, then Mac mini M1), with the local
# llama-server as the fallback. Opt out with AISTACK_REVIEW_GATEWAY=off. The gateway key is never printed and never
# put on a command line: curl reads it from stdin and aider reads it from the environment.
#
# Key order: AISTACK_GATEWAY_KEY, the file ~/.config/llm-gateway/key, Doppler LLM_KEY_<LLM_DEVICE> (when LLM_DEVICE
# is set, for example macbook-m2pro), then Doppler LLM_PUBLIC_API_KEY.
typeset -g _LLM_GW_KEY=""

function _llm_gateway_key() {
  if [[ -z "$_LLM_GW_KEY" ]]; then
    local f="$HOME/.config/llm-gateway/key" name dev
    if [[ -n "${AISTACK_GATEWAY_KEY:-}" ]]; then
      _LLM_GW_KEY="$AISTACK_GATEWAY_KEY"
    elif [[ -r "$f" ]]; then
      _LLM_GW_KEY=$(<"$f")
    elif command -v doppler >/dev/null; then
      dev="${LLM_DEVICE:-}"
      for name in ${dev:+LLM_KEY_${${(U)dev}//-/_}} LLM_PUBLIC_API_KEY; do
        _LLM_GW_KEY=$(doppler secrets get "$name" --project FullHavocJosh --config root_hetzner-cluster --plain 2>/dev/null)
        [[ -n "$_LLM_GW_KEY" ]] && break
      done
    fi
    _LLM_GW_KEY="${_LLM_GW_KEY//[$'\r\n ']/}"
  fi
  [[ -n "$_LLM_GW_KEY" ]]
}

# Healthy backends in dispatch order as TSV "device<TAB>model", or nothing. Reads the pool (all groups, so the older
# build/review split works too). Prints nothing and returns 1 when the gateway, the key or the answer fails.
function _llm_gateway_healthy_backends() {
  local base="${AISTACK_GATEWAY_URL:-https://llm.rollet.family/auto/v1}" out
  _llm_gateway_key || return 1
  out=$(printf 'header = "Authorization: Bearer %s"\n' "$_LLM_GW_KEY" \
    | curl -s -m 3 -K - "${base}/tiers" 2>/dev/null \
    | jq -er '[.groups[]? | .[]? | select(.healthy)] | map("\(.device)\t\(.model)") | .[]' 2>/dev/null) || return 1
  [[ -n "$out" ]] || return 1
  print -r -- "$out"
}

# The gateway base URL for review when any backend is healthy, else return 1.
function _llm_gateway_review_base() {
  case "${AISTACK_REVIEW_GATEWAY:-on}" in off|0|no|false) return 1 ;; esac
  _llm_gateway_healthy_backends >/dev/null || return 1
  print -r -- "${AISTACK_GATEWAY_URL:-https://llm.rollet.family/auto/v1}"
}

# What a review will run on, for gpa's display: "icon|short label|full label". Gateway: the first healthy node in
# dispatch order (the gateway's own spill rule can pick the next one under load, so this names the expected node);
# otherwise the loopback llama-server. The label is decided by the same checks _run_aider_local makes.
function _gpa_review_target() {
  local first dev model
  if [[ "${AISTACK_REVIEW_GATEWAY:-on}" != (off|0|no|false) ]] && first=$(_llm_gateway_healthy_backends 2>/dev/null); then
    first="${first%%$'\n'*}"; dev="${first%%$'\t'*}"; model="${first#*$'\t'}"
    print -r -- "◈|$dev $model|llm.rollet.family auto-review | $dev $model"
  else
    print -r -- "⚪|$(_llamacpp_model_short)|llama.cpp | $(_llamacpp_model_short)"
  fi
}
