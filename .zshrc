# Set the GPG_TTY to be the same as the TTY, either via the env var
# or via the tty command.
# if [ -n "$TTY" ]; then
#   export GPG_TTY=$(tty)
# else
#   export GPG_TTY="$TTY"
# fi

# Nix
if [ -e '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' ]; then
  . '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
fi
# End Nix

# Path to brew
export PATH="/usr/local/bin:/usr/bin:$PATH"

# Path to your terraform installations.
export PATH="$HOME/bin:$PATH"

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

# if [ Darwin = `uname` ]; then
#   source $HOME/.profile-macos
# fi

# SSH_AUTH_SOCK set to GPG to enable using gpgagent as the ssh agent.
# export SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)
# gpgconf --launch gpg-agent

autoload -Uz compinit && compinit

ZINIT_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/zinit/zinit.git"
# Download Zinit, if it's not there yet
if [ ! -d "$ZINIT_HOME" ]; then
   mkdir -p "$(dirname $ZINIT_HOME)"
   git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
fi

source "${ZINIT_HOME}/zinit.zsh"

zinit light ohmyzsh/ohmyzsh
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

# source $HOME/.profile
# source $HOME/.config/tmuxinator/tmuxinator.zsh

if [ Linux = `uname` ]; then
  source $HOME/.profile-linux
fi

setopt auto_cd

#export PATH="/usr/local/opt/curl/bin:$PATH"
# export PATH="$PATH:$HOME/Library/flutter/bin"

export PATH=$PATH:/opt/homebrew/bin

# alias sudo='sudo '
# export LD_LIBRARY_PATH=/usr/local/lib

# Completions
# source <(doctl completion zsh)
# source <(kubectl completion zsh)

# Fix for password store
export PASSWORD_STORE_GPG_OPTS='--no-throw-keyids'

export NVM_DIR="$HOME/.nvm"                            # You can change this if you want.
export NVM_SOURCE="/usr/share/nvm"                     # The AUR package installs it to here.
[ -s "$NVM_SOURCE/nvm.sh" ] && . "$NVM_SOURCE/nvm.sh"  # Load N

bindkey "^P" up-line-or-beginning-search
bindkey "^N" down-line-or-beginning-search

[ -s "$HOME/.svm/svm.sh" ] && source "$HOME/.svm/svm.sh"

# Capslock command
# alias capslock="sudo killall -USR1 caps2esc"

if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    export MOZ_ENABLE_WAYLAND=1
fi

zle_highlight=('paste:none')

# Aliases.
alias clear="clear ; clear ; clear"

alias eza="eza -lh"

alias tree="find . -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'"

alias tfs="tfswitch"
alias tfi="terraform init"
alias tfp="terraform plan"
alias tft="rm -rf .terraform* ; tfswitch ; terraform init ; terraform validate ; terraform plan"
alias tfa="terraform apply"

# alias tft="rm -rf .terraform* ; tfswitch ; terraform init ; terraform validate ; terraform test"
# alias tfp="rm -rf .terraform* ; tfswitch ; terraform init ; terraform validate ; terraform plan"

alias ssm="aws ssm start-session --target"
alias sso='function awslogin() { aws sso login --profile "$1" && export AWS_PROFILE="$1"; }; awslogin' #this allows you to login to the aws sso session
alias ssoswitch='function awsswitch() { export AWS_PROFILE="$1"; } ; awsswitch' #this allows you to switch to another profile you have configured re-using the same session token

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
