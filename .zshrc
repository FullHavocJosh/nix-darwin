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

# Secrets via Doppler, project fullhavocjosh (falls back to ~/.zshrc_envvars)
if command -v doppler &>/dev/null; then
  case "$(scutil --get LocalHostName 2>/dev/null | tr '[:upper:]' '[:lower:]')" in
    macminim1)  _dp_config=root_macmini ;;
    *)          _dp_config=root_macbook ;;
  esac
  set -a
  eval "$(doppler secrets download --no-file --format env \
    --project fullhavocjosh --config "$_dp_config" 2>/dev/null)"
  set +a
  unset _dp_config
else
  [ -f ~/.zshrc_envvars ] && source ~/.zshrc_envvars
fi

[ -f ~/.zshrc_os_macos ] && source ~/.zshrc_os_macos
[ -f ~/.zshrc_personal ] && source ~/.zshrc_personal
[ -f ~/.zshrc_work ] && source ~/.zshrc_work
# Numbered files in each directory load in order; the tuios dir holds the test stack (dev_test, aidev_test, ai_test; RFC ~/.ai/rfcs/2026-10-25-aidev-tuios-test.md)
for _zdir in ~/.zsh_shell ~/.zsh_aliases ~/.zsh_functions/ai ~/.zsh_functions/aws ~/.zsh_functions/git ~/.zsh_functions/tuios; do
  for _zf in "$_zdir"/*.zsh(N); do source "$_zf"; done
done
unset _zdir _zf

# File descriptor limits fix for AWS MCP servers
[ -f ~/.zshrc_ulimit ] && source ~/.zshrc_ulimit

# Set default editor to nvim
export EDITOR="nvim"
export VISUAL="nvim"

# Enable atuin.
export ATUIN_NOBIND="true"
eval "$(atuin init zsh)"
bindkey '^a' atuin-search

# Enable fzf. Its file picker moves from ctrl+t (the tuios prefix) to ctrl+f, and its alt+c directory picker goes
# (aerospace owns alt): cdi (zoxide's picker) picks a directory instead. ctrl+r stays fzf's history; atuin is on ctrl+a.
eval "$(fzf --zsh)"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
for _keymap in emacs viins vicmd; do
  bindkey -M "$_keymap" -r '^T'
  bindkey -M "$_keymap" -r '\ec'
  bindkey -M "$_keymap" '^F' fzf-file-widget
done
unset _keymap

# Enable zoxide. cdi is its interactive picker: zinit's zi alias shadows zoxide's own zi.
eval "$(zoxide init zsh)"
alias cdi='__zoxide_zi'

export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.cargo/bin:$PATH"


