# Free OpenCode Zen model choice lives in ~/.config/aistack/zen_models.py: the models.dev catalog says what is free,
# `opencode models` says what this account is offered, zen-policy.json (from the Zen docs) says which free models are
# zero-retention. The helpers that used to be here called `opencode models --verbose opencode`, which opencode v2
# rejects, so discovery failed silently and a hardcoded "big-pickle" was used no matter what: nothing would have
# noticed Big Pickle turning paid or being retired. Kept as thin wrappers; they print the reason when nothing is free.
# Prints a bare model id; returns 1 when there is no free model.
function _discover_best_free_zen_model() {
  python3 "${AISTACK_DIR:-$HOME/.config/aistack}/zen_models.py" best
}
function _get_free_zen_model() {
  _discover_best_free_zen_model
}

# AI Command Execution Functions

function _validate_opencode_zen() {
  _ai_provider_enabled opencode || return 1
  [[ -n "$OPENCODE_ZEN_API_KEY" ]] && return 0
  [[ -f ~/.zshrc_envvars ]] && grep -q "OPENCODE_ZEN_API_KEY" ~/.zshrc_envvars && return 0
  [[ -f ~/.zshrc_envvars_insecure ]] && grep -q "OPENCODE_ZEN_API_KEY" ~/.zshrc_envvars_insecure && return 0
  [[ -f ~/.config/opencode/.env ]] && grep -q "OPENCODE_ZEN_API_KEY" ~/.config/opencode/.env && return 0
  # Check auth.json for OpenCode Zen API key (injected by nix-darwin activation)
  if [[ -f ~/.local/share/opencode/auth.json ]] && command -v jq &>/dev/null; then
    local opencode_key=$(jq -r '.opencode.key // empty' ~/.local/share/opencode/auth.json 2>/dev/null)
    [[ -n "$opencode_key" ]] && return 0
  fi
  return 1
}

