#!/usr/bin/env bash
# Toggle gaps for the current workspace
# Migrated from omarchy-hyprland-workspace-toggle-gaps

WORKSPACE=$(hyprctl activeworkspace -j | jq -r '.id')
GAPS_IN=$(hyprctl getoption general:gaps_in -j | jq -r '.int')

if [ "$GAPS_IN" -eq 0 ]; then
	# Restore gaps
	hyprctl --batch "keyword general:gaps_in 5 ; keyword general:gaps_out 10"
	notify-send -a "Hyprland" "Gaps enabled"
else
	# Remove gaps
	hyprctl --batch "keyword general:gaps_in 0 ; keyword general:gaps_out 0"
	notify-send -a "Hyprland" "Gaps disabled"
fi
