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
    cp "/Users/jrollet/.wallpapers/wallhaven-7pw1we.jpg" "/Users/Shared/Wallpaper.jpg"
    osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "/Users/jrollet/.wallpapers/wallhaven-7pw1we.jpg"'
    killall Dock
  '';
  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    # Apps installed via nix package must include ${pkgs.APPNAME}
    dock.persistent-apps = [
      "/Applications/Alacritty.app"
      "/Applications/Zen.app"
      "/Applications/Remote Desktop Manager Free.app"
      "/Applications/Slack.app"
      "/Applications/Microsoft Outlook.app"
      "/Applications/Microsoft Teams.app"
    ];
  };
  homebrew = {
    enable = true;
    taps = [
    ];
    # Install Brew Formulas
    brews = [
      "act"
      "k9s"
      "kubectl"
    ];
    # Install Brew Casks
    casks = [
      "citrix-workspace"
      "docker-desktop"
      "lastpass"
      "mqtt-explorer"
      "powershell"
      "remote-desktop-manager-free"
    ];
    # Install App Store Apps, search for ID with "mas search "
    # You must be logged into the Apps Store, and you must have purchased the app
    masApps = {
    };
  };
}
