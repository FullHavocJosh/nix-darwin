if [[ -f "/opt/homebrew/bin/brew" ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

preexec() {
  echo -ne "\033]0;$1\007"
}

precmd() {
  echo -ne "\033]0;${USER}@${HOST}:${PWD}\007"
}

if command -v starship &>/dev/null; then
  eval "$(starship init zsh)"
fi

# Secrets via Doppler (falls back to ~/.zshrc_envvars and ~/.zshrc_envvars_insecure)
if command -v doppler &>/dev/null; then
  _device_config=$(scutil --get LocalHostName 2>/dev/null | tr '[:upper:]' '[:lower:]')
  for _dp in \
    "devices-laptops:${_device_config}" \
    "ai-tools:local" \
    "media-stack:local" \
    "homelab-infra:local" \
    "matrix-homelab:hetzner"; do
    eval "$(doppler secrets download --no-file --format shell \
      --project ${_dp%%:*} --config ${_dp##*:} 2>/dev/null)"
  done
  unset _dp _device_config
  
  # Also load OpenCode Zen API key from .env file if it exists
  if [ -f ~/.config/opencode/.env ]; then
    set -a
    source ~/.config/opencode/.env
    set +a
  fi
else
  [ -f ~/.zshrc_envvars ] && source ~/.zshrc_envvars
  if [ -f ~/.config/opencode/.env ]; then
    set -a
    source ~/.config/opencode/.env
    set +a
  fi
fi
[ -f ~/.zshrc_os_linux ] && source ~/.zshrc_os_linux
[ -f ~/.zshrc_os_macos ] && source ~/.zshrc_os_macos
[ -f ~/.zshrc_shell ] && source ~/.zshrc_shell
[ -f ~/.zshrc_aliases ] && source ~/.zshrc_aliases
[ -f ~/.zshrc_functions_ai ] && source ~/.zshrc_functions_ai
[ -f ~/.zshrc_functions_git ] && source ~/.zshrc_functions_git

# File descriptor limits fix for AWS MCP servers
[ -f ~/.zshrc_ulimit ] && source ~/.zshrc_ulimit

# Set default editor to nvim
export EDITOR="nvim"
export VISUAL="nvim"

# Enable atuin.
export ATUIN_NOBIND="true"
eval "$(atuin init zsh)"
bindkey '^a' atuin-search

# Enable fzf.
eval "$(fzf --zsh)"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Enable zoxide.
eval "$(zoxide init zsh)"

# Added by LM Studio CLI (lms)
export PATH="$PATH:/Users/havoc/.lmstudio/bin"
# End of LM Studio CLI section

export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.cargo/bin:$PATH"
