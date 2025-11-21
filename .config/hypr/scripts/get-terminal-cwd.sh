#!/usr/bin/env bash
# Get the current working directory of the focused terminal and launch a new terminal in that directory
# Works with Konsole (KDE's default terminal)

# Get the PID of the active window
ACTIVE_PID=$(hyprctl activewindow -j | jq -r '.pid')

if [ -z "$ACTIVE_PID" ] || [ "$ACTIVE_PID" = "null" ]; then
	# No active window, launch terminal in home directory
	konsole &
	exit 0
fi

# Try to get the working directory from the process
CWD=$(readlink -f /proc/$ACTIVE_PID/cwd 2>/dev/null)

# If we couldn't get the CWD or it's not valid, try to find a child process (shell)
if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
	# Get the first child process (usually the shell)
	CHILD_PID=$(pgrep -P $ACTIVE_PID | head -n 1)
	if [ -n "$CHILD_PID" ]; then
		CWD=$(readlink -f /proc/$CHILD_PID/cwd 2>/dev/null)
	fi
fi

# If we still don't have a valid directory, use home
if [ -z "$CWD" ] || [ ! -d "$CWD" ]; then
	CWD="$HOME"
fi

# Launch the terminal in the working directory
konsole --workdir "$CWD" &
