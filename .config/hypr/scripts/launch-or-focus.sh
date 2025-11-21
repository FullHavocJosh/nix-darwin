#!/usr/bin/env bash
# Launch an application or focus it if it's already running
# Usage: launch-or-focus.sh <class> <command>

if [ $# -lt 2 ]; then
	echo "Usage: $0 <window_class> <command>"
	exit 1
fi

WINDOW_CLASS="$1"
shift
COMMAND="$@"

# Check if a window with the given class exists
WINDOW_ADDRESS=$(hyprctl clients -j | jq -r ".[] | select(.class == \"$WINDOW_CLASS\") | .address" | head -n 1)

if [ -n "$WINDOW_ADDRESS" ]; then
	# Window exists, focus it
	hyprctl dispatch focuswindow address:$WINDOW_ADDRESS
else
	# Window doesn't exist, launch the application
	$COMMAND &
fi
