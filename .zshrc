# Dynamic Titles
preexec() {
    # Set the title to the command being run
    echo -ne "\033]0;$1\007"
}
precmd() {
    # Set the title to the user@host and path after the command finishes
    echo -ne "\033]0;${USER}@${HOST}:${PWD}\007"
}

# Environmental Variables:
source ~/.zshenv_vars

# OS-Specific Settings #####################################################

# macOS-Specific Settings
if [[ "$(uname)" == "Darwin" ]]; then
  echo "ZSH Configuration for MacOS..."

  # Nix
  if [ -e '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' ]; then
    . '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
  fi
  # End Nix

  # Path to Nix binaries.
  export PATH=$PATH:"/run/current-system/sw/bin"

  # Path to HomeBrew.
  export PATH=$PATH:"/opt/homebrew/bin:/usr/bin"

  # Path to python and pip.
  export PATH=$PATH:"$HOME/Library/Python/3.9/bin"
  export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
  export no_proxy="*"
  export PATH=$PATH:"/opt/homebrew/opt/openssl@3/bin"
  export LDFLAGS="-L/opt/homebrew/opt/openssl@3/lib"
  export CPPFLAGS="-I/opt/homebrew/opt/openssl@3/include"
  export PKG_CONFIG_PATH="/opt/homebrew/opt/openssl@3/lib/pkgconfig"

  # Path to terraform.
  export PATH=$PATH:"$HOME/bin"

  # Path to go.
  export GOPATH=/bin
  export PATH=$PATH:$GOROOT/bin
  export GOPATH=/opt/homebrew/Cellar/go/1.23.2
  export GOROOT=/opt/homebrew/Cellar/go/1.23.2/libexec

  # Path to tfswitch.
  export PATH=$PATH:"$HOME/opt/homebrew/bin/tfswitch"

  # Added by LM Studio CLI (lms)
  export PATH=$PATH:"/Users/jrollet/.lmstudio/bin"

  # Automatically activate Ansible virtual environment
  if [ -d "$HOME/ansible-venv" ]; then
      source "$HOME/ansible-venv/bin/activate"
  else
      echo "Creating Ansible virtual environment..."
      python3 -m venv ~/ansible-venv
      source "$HOME/ansible-venv/bin/activate"
      echo "Virtual environment created and activated."
  fi
fi

############################################################################

# Linux-Specific Settings
if [[ "$(uname)" == "Linux" ]]; then
  echo "ZSH Configuration for Linux..."

  # Prepend Homebrew's bin directory to your PATH
  export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"

  . "$HOME/.atuin/bin/env"

  if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
      export MOZ_ENABLE_WAYLAND=1
  fi

  HISTFILE=~/.zsh_history
  HISTSIZE=10000
  SAVEHIST=1000
  setopt SHARE_HISTORY

fi

############################################################################

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

setopt auto_cd

# Vim, always Vim.
export EDITOR=vim
export VISUAL=vim

# Fix for password store
export PASSWORD_STORE_GPG_OPTS='--no-throw-keyids'

export NVM_DIR="$HOME/.nvm"
export NVM_SOURCE="/usr/share/nvm"
[ -s "$NVM_SOURCE/nvm.sh" ] && . "$NVM_SOURCE/nvm.sh"

bindkey "^P" up-line-or-beginning-search
bindkey "^N" down-line-or-beginning-search

[ -s "$HOME/.svm/svm.sh" ] && source "$HOME/.svm/svm.sh"

zle_highlight=('paste:none')

# Aliases - SSH Targets.
alias sshmacbook='ssh -i ~/.ssh/id_ed25519 havoc@Joshs-MacBook-Pro.rollet.family'
alias sshg14='ssh -i ~/.ssh/id_ed25519 root@Joshs-G14.rollet.family' 
alias sshazeroth='ssh -i ~/.ssh/id_ed25519 root@azerothcore.rollet.family'
alias sshtestazeroth='ssh -i ~/.ssh/id_ed25519 root@testing-azerothcore.rollet.family'
alias sshmini='ssh -i ~/.ssh/id_ed25519 havoc@macOS-Mac-mini.rollet.family'
alias ssh705='ssh -i ~/.ssh/id_ed25519 havoc@705-G4-Fedora.rollet.family'
alias sshdeck='ssh -i ~/.ssh/id_ed25519 havoc@Joshs-SteamDeck.rollet.family'

# Aliases - NeoVIM Development.
alias nxvim="cd ~/nix-darwin && tmux new-session -A -s nix-darwin"
alias psvim="cd ~/pscloudops/ && tmux new-session -A -s pscloudops"

# Aliases - Common Shortcuts.
alias clear="clear ; clear ; clear"
alias eza="eza -la"
alias ls="eza"
alias tree="find . -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'"
alias pip="pip3"
alias python="/usr/bin/python3"


# Aliases - Terraform.
alias tfs="tfswitch"
alias tfi="terraform init"
alias tfa="terraform apply"
alias tft="rm -rf .terraform* ; tfswitch ; terraform init -upgrade ; terraform validate ; terraform test"
alias tfp="rm -rf .terraform* ; tfswitch ; terraform init -upgrade ; terraform validate ; terraform plan"

# Aliases - AWS.
alias asl='aws sso login --sso-session aws'
alias sso='function awslogin() { aws sso login --profile "$1" && export AWS_PROFILE="$1"; }; awslogin' #this allows you to login to the aws sso session
alias ssoswitch='function awsswitch() { export AWS_PROFILE="$1"; unset AWS_ACCESS_KEY_ID; unset AWS_SECRET_ACCESS_KEY; }; awsswitch' #this allows you to switch to another profile you have configured re-using the same session token
alias ssoexport='eval "$(aws configure export-credentials --profile $AWS_PROFILE --format env)"'

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

# Added by LM Studio CLI (lms)
export PATH="$PATH:/Users/havoc/.lmstudio/bin"
# End of LM Studio CLI section

# Set environmental variables for AWS
function asc() {
  if [ "$1" = "clear" ]; then
    unset -m "AWS_*"
    echo "AWS environment variables unset"
  else
    eval "$(aws configure export-credentials --profile $1 --format env)"
    export AWS_PROFILE=$1
    echo "AWS environment variables set"
  fi
}
