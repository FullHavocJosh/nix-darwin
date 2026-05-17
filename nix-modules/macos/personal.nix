{ pkgs, ... }:
let
  wallpaper = "/Users/havoc/.wallpapers/wallhaven-5yk6k9.jpg";
in
{
  system.activationScripts.script.text = ''
    #!/usr/bin/env bash
    echo "Stowing dotfiles as user $(whoami)..."
    cd "/Users/havoc/nix-darwin" || { echo "Failed to cd into /Users/havoc/nix-darwin"; exit 1; }
    ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow dotfiles"; exit 1; }
    echo "Finished Stowing dotfiles..."

    echo "Setting wallpaper..."
    osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "${wallpaper}"'

    echo "Syncing HostName to LocalHostName..."
    scutil --set HostName "$(scutil --get LocalHostName)"

    # Inject OpenCode Zen API key from Doppler (personal devices only)
    # Run as user 'havoc' since Doppler auth is per-user and activation runs as root
    echo "Fetching OpenCode Zen API key from Doppler..."
    USER_HOME="/Users/havoc"
    OPENCODE_CONFIG_DIR="$USER_HOME/.config/opencode"
    OPENCODE_ENV_FILE="$OPENCODE_CONFIG_DIR/.env"
    DOPPLER_BIN="/opt/homebrew/bin/doppler"
    DOPPLER_CONFIG="$USER_HOME/.doppler/.doppler.yaml"

    if [ -x "$DOPPLER_BIN" ] && [ -f "$DOPPLER_CONFIG" ]; then
      # Create directory as user
      mkdir -p "$OPENCODE_CONFIG_DIR"
      
      # Fetch OPENCODE_ZEN_API_KEY from Doppler as user
      # Project: devices-laptops, Config: macbookprom2pro
      # Use sudo -u to run as havoc with their HOME environment
      DOPPLER_API_KEY=$(sudo -u havoc HOME="$USER_HOME" "$DOPPLER_BIN" secrets get OPENCODE_ZEN_API_KEY --project devices-laptops --config macbookprom2pro --plain 2>/dev/null)
      
      if [ -n "$DOPPLER_API_KEY" ]; then
        echo "ANTHROPIC_API_KEY=$DOPPLER_API_KEY" > "$OPENCODE_ENV_FILE"
        chown havoc:staff "$OPENCODE_ENV_FILE"
        chmod 600 "$OPENCODE_ENV_FILE"
        echo "OpenCode Zen API key successfully injected to $OPENCODE_ENV_FILE"
      else
        echo "Warning: Failed to fetch OPENCODE_ZEN_API_KEY from Doppler."
        echo "Make sure you're authenticated with: doppler login"
        echo "And verify the secret exists in project 'devices-laptops', config 'macbookprom2pro'"
      fi
    else
      echo "Warning: Doppler CLI not found at $DOPPLER_BIN or config missing. OpenCode Zen API key not injected."
    fi

  '';

  launchd.user.agents.ollama = {
    serviceConfig = {
      ProgramArguments = [
        "/Applications/Ollama.app/Contents/Resources/ollama"
        "serve"
      ];
      EnvironmentVariables = {
        OLLAMA_HOST = "0.0.0.0:11434";
        OLLAMA_FLASH_ATTENTION = "1";
        OLLAMA_KV_CACHE_TYPE = "q8_0";
      };
      KeepAlive = true;
      RunAtLoad = true;
      StandardOutPath = "/tmp/ollama.log";
      StandardErrorPath = "/tmp/ollama.error.log";
      LimitLoadToSessionType = [
        "Aqua"
        "Background"
        "LoginWindow"
        "StandardIO"
        "System"
      ];
    };
  };

  system.defaults = {
    dock.persistent-apps = [ ];
  };
  homebrew = {
    enable = true;
    taps = [
      "dopplerhq/cli"
      "minio/stable"
      "vitobotta/tap"
    ];
    brews = [
      "dopplerhq/cli/doppler"
      "helm"
      "k9s"
      "kubectl"
      "minio/stable/mc"
      "tailscale"
      "vitobotta/tap/hetzner_k3s"
    ];
    casks = [
      "battle-net"
      "curseforge"
      "element"
      "obsidian"
      "ollama-app"
      "orion"
      "plex"
      "plexamp"
      "proton-drive"
      "protonvpn"
      "proton-mail"
      "rustdesk"
      "steam"
      "whisky"
    ];
    masApps = { };
  };
}
