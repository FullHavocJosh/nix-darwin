#!/usr/bin/env bash
# Taken from: # Taken from: https://github.com/julian-heng/yabai-config/blob/master/scripts/open_iterm2.sh
# Detects if iTerm2 is running
if ! pgrep -f "Alacritty" > /dev/null 2>&1; then
    open -a "/Applications/Alacritty.app"
else
    # Create a new window
    script='tell application "Alacritty" to create window with default profile'
    ! osascript -e "${script}" > /dev/null 2>&1 && {
        # Get pids for any app with "Alacritty" and kill
        while IFS="" read -r pid; do
            kill -15 "${pid}"
        done < <(pgrep -f "Alacritty")
        open -a "/Applications/Alacritty.app"
    }
fi
