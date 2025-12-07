{ pkgs, config, ... }:
{

  ###########################################
  ### MacOS Settings for Personal Devices ###
  ###########################################

  system.activationScripts.script.text = ''
    #!/usr/bin/env bash
    echo "Stowing dotfiles as user $(whoami)..."
    cd "/Users/havoc/nix-darwin" || { echo "Failed to cd into /Users/havoc/nix-darwin"; exit 1; }
    ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow dotfiles"; exit 1; }
    echo "Finished Stowing dotfiles..."

    echo "Setting wallpaper..."
    osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "/Users/havoc/.wallpapers/wallhaven-2yxj8m.jpg"'
  '';

  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    dock.persistent-apps = [
      "/Applications/Alacritty.app"
      "/Applications/Zen.app"
      "/System/Applications/Music.app"
      "/System/Applications/Notes.app"
      "/Applications/Obsidian.app"
      "/System/Applications/Freeform.app"
      "/Applications/Discord.app"
      "/System/Applications/Messages.app"
      "/Applications/Proton Mail.app"
    ];
  };
  homebrew = {
    enable = true;
    taps = [
    ];
    # Install Brew Formulas
    brews = [
    ];
    # Install Brew Casks
    casks = [
      "battle-net"
      "curseforge"
      "discord"
      "obsidian"
      "ollama"
      "plex"
      "plexamp"
      "proton-drive"
      "protonvpn"
      "proton-mail"
      "rustdesk"
      "steam"
      "whisky"
    ];
    # Install App Store Apps, search for ID with "mas search "
    # You must be logged into the Apps Store, and you must have purchased the app
    masApps = {
      "WireGuard" = 1451685025;
    };
  };
}
