function _ensure_envvars_permissions() {
  [[ -f ~/.zshrc_envvars ]] && chmod 600 ~/.zshrc_envvars 2>/dev/null

  if [[ -L ~/.zshrc_envvars_insecure ]]; then
    local target=$(readlink -f ~/.zshrc_envvars_insecure 2>/dev/null || realpath ~/.zshrc_envvars_insecure 2>/dev/null)
    [[ -f "$target" ]] && chmod 600 "$target" 2>/dev/null
  elif [[ -f ~/.zshrc_envvars_insecure ]]; then
    chmod 600 ~/.zshrc_envvars_insecure 2>/dev/null
  fi
}

_ensure_envvars_permissions
