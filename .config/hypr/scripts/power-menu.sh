#!/usr/bin/env bash
# Power menu using KDE's native dialogs (default on Nobara)
# Provides options for logout, reboot, shutdown, lock, suspend

# Check if kdialog is available (KDE default)
if command -v kdialog &>/dev/null; then
	OPTIONS="Lock\nLogout\nSuspend\nReboot\nShutdown"
	SELECTED=$(echo -e "$OPTIONS" | kdialog --menu "Power Options" \
		1 "Lock" \
		2 "Logout" \
		3 "Suspend" \
		4 "Reboot" \
		5 "Shutdown" 2>/dev/null)

	case $SELECTED in
	1) hyprlock ;;
	2) hyprctl dispatch exit ;;
	3) systemctl suspend ;;
	4) systemctl reboot ;;
	5) systemctl poweroff ;;
	esac
else
	# Fallback: Use KDE's system logout directly
	qdbus org.kde.ksmserver /KSMServer org.kde.KSMServerInterface.logout -1 -1 -1
fi
