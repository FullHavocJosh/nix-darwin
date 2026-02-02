{ pkgs, ... }:
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

  # Configure Ollama service to listen on all interfaces
  launchd.user.agents.ollama = {
    serviceConfig = {
      ProgramArguments = [
        "/Applications/Ollama.app/Contents/Resources/ollama"
        "serve"
      ];
      EnvironmentVariables = {
        OLLAMA_HOST = "0.0.0.0:11434";
      };
      KeepAlive = true;
      RunAtLoad = true;
      StandardOutPath = "/tmp/ollama.log";
      StandardErrorPath = "/tmp/ollama.error.log";
    };
  };

  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    dock.persistent-apps = [
      "/Applications/Alacritty.app"
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
      "ollama-app"
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
