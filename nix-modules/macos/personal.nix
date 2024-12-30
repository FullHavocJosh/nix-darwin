{ pkgs, config, ... }: {

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
    osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "/Users/havoc/.wallpapers/wallhaven-v9zlxp.jpg"'
  '';

  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    dock.persistent-apps = [
      "/Applications/alacritty.app"
      "/Applications/GoLand.app"
      "/System/Cryptexes/App/System/Applications/Safari.app"
      "/System/Applications/Music.app"
      "/Applications/Obsidian.app"
      "/System/Applications/Freeform.app"
      "/Applications/Discord.app"
      "/System/Applications/Messages.app"
      "/Applications/Telegram Desktop.app"
      "/Applications/Proton Mail.app"
      "/Applications/Proton Pass.app"
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
      "google-chrome"
      "obsidian"
      "plex"
      "proton-drive"
      "protonvpn"
      "proton-mail"
      "steam"
      "telegram-desktop"
      "ultimaker-cura"
      "whisky"
    ];
    # Install App Store Apps, search for ID with "mas search "
    # You must be logged into the Apps Store, and you must have purchased the app
    masApps = {
      "Noir for Safari" = 1592917505;
      "Proton Pass for Safari" = 6502835663;
      "SponsorBlock for Safari" = 1573461917;
    };
  };
}
