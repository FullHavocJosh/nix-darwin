# gpr never calls an AI provider (branch/PR creation only), so this is a
# plain alias for interface symmetry with gpc-local/gpa-local, not a
# behavioral wrapper.
alias gpr-local='gpr_func'
alias gpr='gpr_func'
alias gpa-clear-cache='_gpa_clear_cache'
alias gp='git pull && git submodule update --init --recursive'

