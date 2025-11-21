#!/usr/bin/env bash
# Switch between available audio outputs
# Uses wpctl (PipeWire/WirePlumber) which is standard on Nobara/Fedora
# Uses KDE's notification system via kdialog

# Get list of all sinks with their IDs and names
SINKS=$(wpctl status | grep -A 50 "Audio" | grep "│  ├─" | grep -v "Monitor")

# Extract sink IDs
SINK_IDS=($(echo "$SINKS" | awk '{print $2}' | tr -d '.'))

if [ ${#SINK_IDS[@]} -le 1 ]; then
	kdialog --passivepopup "No other audio output available" 3 --title "Audio Output" 2>/dev/null ||
		notify-send -a "Audio Output" "No other audio output available"
	exit 0
fi

# Get current default sink ID
CURRENT_ID=$(wpctl status | grep "Audio" -A 50 | grep "│  ├─.*\*" | awk '{print $2}' | tr -d '.*')

# Find current sink index
CURRENT_INDEX=-1
for i in "${!SINK_IDS[@]}"; do
	if [ "${SINK_IDS[$i]}" = "$CURRENT_ID" ]; then
		CURRENT_INDEX=$i
		break
	fi
done

# Calculate next sink index (cycle through available sinks)
NEXT_INDEX=$(((CURRENT_INDEX + 1) % ${#SINK_IDS[@]}))
NEXT_ID="${SINK_IDS[$NEXT_INDEX]}"

# Switch to next sink
wpctl set-default "$NEXT_ID"

# Get the friendly name for notification
SINK_NAME=$(wpctl status | grep "$NEXT_ID" | sed 's/.*├─ //; s/\[.*//; s/^ *//; s/ *$//')

# Use KDE notification with fallback to notify-send
kdialog --passivepopup "Switched to: $SINK_NAME" 3 --title "Audio Output" 2>/dev/null ||
	notify-send -a "Audio Output" "Switched to: $SINK_NAME"
