    # Run user-specific configuration as the primary user
    USER_NAME=@primaryUserQuoted@
    USER_HOME=$(eval echo ~$USER_NAME)
    
    sudo --set-home -u "$USER_NAME" bash <<'USERSCRIPT'
