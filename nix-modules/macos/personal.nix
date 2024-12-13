{ pkgs, config, ... }: {

  ###########################################
  ### MacOS Settings for Personal Devices ###
  ###########################################

  system.activationScripts.script.text = ''
    echo "Stowing dotfiles..."
    cd /Users/havoc/nix-darwin || { echo "Failed to cd into ~/nix-darwin/dotfiles"; exit 1; }
    echo "Stowing $dir..."
    ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow ."; exit 1; }
  '';

  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    dock.persistent-apps = [
      "/Applications/Hyper.app"
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
      "warrensbox/tap"
    ];
    # Install Brew Formulas
    brews = [
      "kanata"
      "wireguard-go"
    ];
    # Install Brew Casks
    casks = [
      "battle-net"
      "curseforge"
      "discord"
      "chromium"
      "karabiner-elements"
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
