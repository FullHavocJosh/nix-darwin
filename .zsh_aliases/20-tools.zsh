alias clear="clear ; clear ; clear"
alias eza="eza -la"
alias pip="pip3"
alias python="/usr/bin/python3"
alias spf="spf -c ~/.config/superfile/config.toml"

alias tfs="rm -rf .terraform* ; tfswitch"
alias tfi="rm -rf .terraform* ; tfswitch ; terraform init -upgrade"
alias tft="rm -rf .terraform* ; tfswitch ; terraform init -upgrade ; terraform validate ; terraform test"
alias tfp="rm -rf .terraform* ; tfswitch ; terraform init -upgrade ; terraform validate ; terraform plan"
alias tfa="rm -rf .terraform* ; tfswitch ; terraform init -upgrade ; terraform validate ; terraform plan ; terraform apply"

alias asl='aws sso login --sso-session aws'
alias sso='function awslogin() { aws sso login --profile "$1" && export AWS_PROFILE="$1"; }; awslogin'
alias ssoswitch='function awsswitch() { export AWS_PROFILE="$1"; unset AWS_ACCESS_KEY_ID; unset AWS_SECRET_ACCESS_KEY; }; awsswitch'
alias ssoexport='eval "$(aws configure export-credentials --profile $AWS_PROFILE --format env)"'

