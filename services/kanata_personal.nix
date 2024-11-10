{ conig, pkgs, ... }: {
  # Ensure Homebrew is enabled for this package if it's not in nixpkgs
  homebrew = {
    enable = true;
  };

  # Ensure that Karabiner DriverKiet is installed
  system.activationScripts.kanataInstall = {
    text = ''
      echo "Installing Karabiner DriverKit for Kanata..."
      brew install kanata || true
      brew install --cask karabiner-elements || true
      echo "Activating Karabiner VirtualHID Driver..."
      sudo /Applications/.Karabiner-VirtualHIDDevice-Manager.app/Contents/MacOS/Karabiner-VirtualHIDDevice-Manager activate
    '';
    enable = true;
  };

  # launchctl load ~/Library/LaunchAgents/local.kanata.plist
  # cp /etc/local.kanata.plist ~/Library/LaunchAgents/
  # launchctl load ~/Library/LaunchAgents/local.kanata.plist
  environment.etc."local.kanata.plist".text = ''
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        <key>Label</key>
        <string>io.havoc.kanata</string>

        <key>ProgramArguments</key>
        <array>
            <string>/Users/havoc/.cargo/bin/kanata</string>
            <string>-c</string>
            <string>/Users/havoc/.config/kanata/config.kdb</string>
        </array>

        <key>RunAtLoad</key>
        <true/>

        <key>KeepAlive</key>
        <true/>

        <key>StandardOutPath</key>
        <string>/Library/Logs/Kanata/kanata.out.log</string>

        <key>StandardErrorPath</key>
        <string>/Library/Logs/Kanata/kanata.err.log</string>
    </dict>
    </plist>
  '';
}
