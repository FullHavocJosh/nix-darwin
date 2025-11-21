#!/usr/bin/env bash
# Screen recording launcher
# Uses KDE's Spectacle (default on Nobara) or launches OBS Studio

# Check if Spectacle supports video recording (newer versions do)
if spectacle --help 2>&1 | grep -q "record"; then
	# Use Spectacle for screen recording (KDE Plasma 6.0+)
	spectacle --record --background
	notify-send -a "Screen Recording" "Recording started" "Using Spectacle"
else
	# Launch OBS Studio (commonly pre-installed on Nobara)
	if command -v obs &>/dev/null; then
		obs &
		notify-send -a "Screen Recording" "OBS Studio launched" "Configure and start recording"
	# Fallback to SimpleScreenRecorder (lighter alternative)
	elif command -v simplescreenrecorder &>/dev/null; then
		simplescreenrecorder &
		notify-send -a "Screen Recording" "SimpleScreenRecorder launched"
	else
		notify-send -a "Screen Recording" "No recorder found" "Install OBS or SimpleScreenRecorder"
	fi
fi
