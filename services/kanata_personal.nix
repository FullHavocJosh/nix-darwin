{ config, pkgs, ... }: {
  # Enable Homebrew for packages outside of nixpkgs
  homebrew.enable = true;

  # Single kanataSetup activation script with detailed logging
  system.activationScripts.kanataSetup = {
    text = ''
      echo "Starting kanataSetup activation script..." | tee -a /Users/havoc/.config/kanata/scripts/setup.log
      if [ -x /Users/havoc/.config/kanata/scripts/setup_kanata.sh ]; then
        echo "setup_kanata.sh exists and is executable." | tee -a /Users/havoc/.config/kanata/scripts/setup.log
        /Users/havoc/.config/kanata/scripts/setup_kanata.sh >> /Users/havoc/.config/kanata/scripts/setup.log 2>&1
        echo "setup_kanata.sh completed." | tee -a /Users/havoc/.config/kanata/scripts/setup.log
      else
        echo "setup_kanata.sh is missing or not executable." | tee -a /Users/havoc/.config/kanata/scripts/setup.log
      fi
    '';
    enable = true;
  };

  # LaunchAgent plist configuration for Kanata
  environment.etc."local_kanata_plist".text = ''
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
        <string>~/Library/Logs/Kanata/kanata.out.log</string>
        <key>StandardErrorPath</key>
        <string>~/Library/Logs/Kanata/kanata.err.log</string>
    </dict>
    </plist>
  '';
}
