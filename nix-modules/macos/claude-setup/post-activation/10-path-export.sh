    # sudo -u spawns a non-login, non-interactive shell -- it never reads
    # .zprofile/.zshrc, so PATH here is whatever sudo's secure_path
    # default is (typically /usr/bin:/bin:/usr/sbin:/sbin), NOT Homebrew's
    # bin dirs. Confirmed: this is why brew/npm/node all came back
    # "command not found" here despite being freshly installed moments
    # earlier in this same activation run. /run/current-system/sw/bin is
    # nix-darwin's own system path -- it's where the real `bash` (5.x)
    # lives, not /opt/homebrew; macOS's /bin/bash is permanently stuck at
    # 3.2 (Apple never updates it, GPLv2 vs GPLv3 licensing), which is too
    # old for token-optimizer-mcp's install-hooks.sh ("Bash 4.0 or later
    # is required") -- confirmed hitting exactly that inside this heredoc
    # even after adding the Homebrew paths below.
    export PATH="/run/current-system/sw/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

