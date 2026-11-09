export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

setopt auto_cd

# Vim, always Vim.
export EDITOR=vim
export VISUAL=vim

# Fix for password store
export PASSWORD_STORE_GPG_OPTS='--no-throw-keyids'

# Increase file descriptor limits for AWS MCP servers and other tools
ulimit -n 4096

export NVM_DIR="$HOME/.nvm"
export NVM_SOURCE="/usr/share/nvm"
[ -s "$NVM_SOURCE/nvm.sh" ] && . "$NVM_SOURCE/nvm.sh"

[ -s "$HOME/.svm/svm.sh" ] && source "$HOME/.svm/svm.sh"

