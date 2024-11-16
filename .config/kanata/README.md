sudo cp ~/nix-darwin/.config/kanata/com.havoc.kanata.plist /Library/LaunchDaemons

sudo launchctl load /Library/LaunchDaemons/com.havoc.kanata.plist

sudo launchctl start com.havoc.kanata