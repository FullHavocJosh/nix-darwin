# setup_kanata.sh
#!/usr/bin/env bash

echo "Activating Karabiner VirtualHID Driver..."
sudo /Applications/.Karabiner-VirtualHIDDevice-Manager.app/Contents/MacOS/Karabiner-VirtualHIDDevice-Manager activate

# Copy and load Kanata plist
echo "Copying and loading Kanata LaunchAgent plist..."
cp /etc/local_kanata_plist ~/Library/LaunchAgents/local_kanata.plist
sudo launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local_kanata.plist || true
