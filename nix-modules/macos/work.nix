{ pkgs, config, ... }: {

  #######################################
  ### MacOS Settings for Work Devices ###
  #######################################

  system.activationScripts.script.text = ''
    #!/usr/bin/env bash
    echo "Stowing dotfiles..."
    cd "/Users/jrollet/nix-darwin" || { echo "Failed to cd into /Users/jrollet/nix-darwin"; exit 1; }
    ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow dotfiles"; exit 1; }
    echo "Finished Stowing dotfiles..."

    echo "Setting wallpaper..."
    osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "/Users/jrollet/.wallpapers/wallhaven-gj6xwq.jpg"'
  '';
  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    # Apps installed via nix package must include ${pkgs.APPNAME}
    dock.persistent-apps = [
      "/Applications/Alacritty.app"
      "/Applications/GoLand.app"
      "/Applications/Zen Browser.app"
      "/Applications/Remote Desktop Manager Free.app"
      "/Applications/Slack.app"
      "/Applications/Microsoft Outlook.app"
      "/Applications/Proton Pass.app"
      "/Applications/LastPass.app"
      "/Applications/LM-Studio.app"
    ];
  };
  homebrew = {
    enable = true;
    taps = [
    ];
    # Install Brew Formulas
    brews = [ ];
    # Install Brew Casks
    casks = [
      "firefox"
      "citrix-workspace"
      "lastpass"
      "mqtt-explorer"
      "powershell"
      "remote-desktop-manager-free"
    ];
    # Install App Store Apps, search for ID with "mas search "
    # You must be logged into the Apps Store, and you must have purchased the app
    masApps = {
      "VMware Remote Console" = 1230249825;
      "Xcode" = 497799835;
    };
  };
}
