if [[ -f "/opt/homebrew/bin/brew" ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

preexec() {
    echo -ne "\033]0;$1\007"
}

precmd() {
    echo -ne "\033]0;${USER}@${HOST}:${PWD}\007"
}

if command -v starship &> /dev/null; then
    eval "$(starship init zsh)"
fi

[ -f ~/.zshrc_envvars ] && source ~/.zshrc_envvars
[ -f ~/.zshrc_envvars_insecure ] && source ~/.zshrc_envvars_insecure
[ -f ~/.zshrc_os_linux ] && source ~/.zshrc_os_linux
[ -f ~/.zshrc_os_macos ] && source ~/.zshrc_os_macos
[ -f ~/.zshrc_shell ] && source ~/.zshrc_shell
[ -f ~/.zshrc_aliases ] && source ~/.zshrc_aliases
[ -f ~/.zshrc_functions ] && source ~/.zshrc_functions

# File descriptor limits fix for AWS MCP servers
[ -f ~/.zshrc_ulimit ] && source ~/.zshrc_ulimit

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

