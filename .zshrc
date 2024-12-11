# Dynamic Titles
preexec() {
    # Set the title to the command being run
    echo -ne "\033]0;$1\007"
}
precmd() {
    # Set the title to the user@host and path after the command finishes
    echo -ne "\033]0;${USER}@${HOST}:${PWD}\007"
}

# Nix
if [ -e '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' ]; then
  . '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
fi
# End Nix

# Start Kitty Socket
export KITTY_LISTEN_ON="unix:/tmp/kitty.socket"

# Path to Nix binaries.
export PATH="/run/current-system/sw/bin:$PATH"

# Path to HomeBrew.
export PATH="/opt/homebrew/bin:/usr/bin:$PATH"

# Path to python and pip.
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export no_proxy="*"

# Path to go.
export GOPATH=/opt/homebrew/Cellar/go/1.23.2
export GOROOT=/opt/homebrew/Cellar/go/1.23.2/libexec
export PATH=$PATH:$GOPATH/bin
export PATH=$PATH:$GOROOT/bin

# Path to ovftool.
export PATH=$PATH:/opt/homebrew/bin/ovftool

# Environmental Variables:
source ~/.zshenv_vars

autoload -Uz compinit && compinit

ZINIT_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/zinit/zinit.git"
# Download Zinit, if it's not there yet
if [ ! -d "$ZINIT_HOME" ]; then
   mkdir -p "$(dirname $ZINIT_HOME)"
   git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
fi

source "${ZINIT_HOME}/zinit.zsh"

zinit snippet OMZP::git
zinit snippet OMZP::sudo
zinit snippet OMZP::aws
zinit snippet OMZP::kubectl
zinit snippet OMZP::kubectx
zinit snippet OMZP::rust
zinit snippet OMZP::command-not-found

zinit light zsh-users/zsh-completions
zinit light zsh-users/zsh-autosuggestions
zinit light zsh-users/zsh-syntax-highlighting

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

if [ Linux = `uname` ]; then
  source $HOME/.profile-linux
fi

setopt auto_cd

# Vim, always Vim.
export EDITOR=vim
export VISUAL=vim

# Fix for password store
export PASSWORD_STORE_GPG_OPTS='--no-throw-keyids'

export NVM_DIR="$HOME/.nvm"                            # You can change this if you want.
export NVM_SOURCE="/usr/share/nvm"                     # The AUR package installs it to here.
[ -s "$NVM_SOURCE/nvm.sh" ] && . "$NVM_SOURCE/nvm.sh"  # Load N

bindkey "^P" up-line-or-beginning-search
bindkey "^N" down-line-or-beginning-search

[ -s "$HOME/.svm/svm.sh" ] && source "$HOME/.svm/svm.sh"

if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    export MOZ_ENABLE_WAYLAND=1
fi

zle_highlight=('paste:none')

# Aliases.
alias nxvim="cd ~/nix-darwin && tmux new-session -A -s nix-darwin"
alias psvim="cd ~/pscloudops/ && tmux new-session -A -s pscloudops"

alias clear="clear ; clear ; clear"

alias eza="eza -la"
alias ls="eza"

alias tree="find . -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'"

alias tfs="tfswitch"
alias tfi="terraform init"
alias tfa="terraform apply"

alias tft="rm -rf .terraform* ; tfswitch ; terraform init ; terraform validate ; terraform test"
alias tfp="rm -rf .terraform* ; tfswitch ; terraform init ; terraform validate ; terraform plan"

alias ssm="aws ssm start-session --target"
alias sso='function awslogin() { aws sso login --profile "$1" && export AWS_PROFILE="$1"; }; awslogin' #this allows you to login to the aws sso session
alias ssoswitch='function awsswitch() { export AWS_PROFILE="$1"; } ; awsswitch' #this allows you to switch to another profile you have configured re-using the same session token

alias pip="pip3"

# Enable atuin.
eval "$(atuin init zsh)"

# Enable fzf.
eval "$(fzf --zsh)"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
alias python=/usr/bin/python3

# Enable oh-my-posh.
if [ "$TERM_PROGRAM" != "Apple_Terminal" ]; then
  eval "$(oh-my-posh init zsh)"
fi

eval "$(oh-my-posh init zsh --config $HOME/.config/ohmyposh/zen.toml)"
