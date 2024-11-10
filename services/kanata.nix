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

  launchd.userAgents.kanata  = {
  enable = true;
    description = "Kanata Input Remapper";
    startAt = "loginwindow";
    script = ''
      exec /opt/homebrew/bin/kanata --config ${builtins.getEnv "HOME"}/.config/kanata/config.kdb
    '';
    serviceConfig = {
      KeepAlive = true;
      RunAtLoad = true;
      StandardErrorPath = "/var/log/kanata.log";
      StandardOutPath = "/var/log/kanata.log";
    };
  };
}