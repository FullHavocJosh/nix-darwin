# Dynamic Titles
preexec() {
    # Set the title to the command being run
    echo -ne "\033]0;$1\007"
}
precmd() {
    # Set the title to the user@host and path after the command finishes
    echo -ne "\033]0;${USER}@${HOST}:${PWD}\007"
}

# Environmental Variables Secure
[ -f ~/.zshrc_envvars ] && source ~/.zshrc_envvars

# Environmental Variables Insecure
[ -f ~/.zshrc_envvars_insecure ] && source ~/.zshrc_envvars_insecure

# OS-specific settings (macOS/Linux paths and configurations)
[ -f ~/.zshrc_os_linux ] && source ~/.zshrc_os_linux
[ -f ~/.zshrc_os_macos ] && source ~/.zshrc_os_macos

# Shell configuration (zinit, plugins, basic settings)
[ -f ~/.zshrc_shell ] && source ~/.zshrc_shell

# Aliases (SSH, development shortcuts, common commands)
[ -f ~/.zshrc_aliases ] && source ~/.zshrc_aliases

# Custom functions
[ -f ~/.zshrc_functions ] && source ~/.zshrc_functions

# Enable atuin.
export ATUIN_NOBIND="true"
eval "$(atuin init zsh)"
bindkey '^a' atuin-search

# Enable fzf.
eval "$(fzf --zsh)"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Enable oh-my-posh.
if [ "$TERM_PROGRAM" != "Apple_Terminal" ]; then
  eval "$(oh-my-posh init zsh)"
fi
eval "$(oh-my-posh init zsh --config $HOME/.config/ohmyposh/zen.toml)"

# Enable zoxide.
eval "$(zoxide init zsh)"

# Added by LM Studio CLI (lms)
export PATH="$PATH:/Users/havoc/.lmstudio/bin"
# End of LM Studio CLI section

