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
    OPENCODE_DATA_DIR="$USER_HOME/.local/share/opencode"
    OPENCODE_AUTH_FILE="$OPENCODE_DATA_DIR/auth.json"
    DOPPLER_BIN="/opt/homebrew/bin/doppler"
    DOPPLER_CONFIG="$USER_HOME/.doppler/.doppler.yaml"

    if [ -x "$DOPPLER_BIN" ] && [ -f "$DOPPLER_CONFIG" ]; then
      # Create directory as user
      mkdir -p "$OPENCODE_DATA_DIR"
      
      # Fetch OPENCODE_ZEN_API_KEY from Doppler as user
      # Project: devices-laptops, Config: macbookprom2pro
      # Use sudo -u to run as havoc with their HOME environment
      DOPPLER_API_KEY=$(sudo -u havoc HOME="$USER_HOME" "$DOPPLER_BIN" secrets get OPENCODE_ZEN_API_KEY --project devices-laptops --config macbookprom2pro --plain 2>/dev/null)
      
      if [ -n "$DOPPLER_API_KEY" ]; then
        # Read existing auth.json if it exists, otherwise start with empty object
        if [ -f "$OPENCODE_AUTH_FILE" ]; then
          EXISTING_AUTH=$(cat "$OPENCODE_AUTH_FILE")
        else
          EXISTING_AUTH="{}"
        fi
        
        # Inject OpenCode Zen credentials into auth.json using jq
        # Keep existing providers (like github-copilot) and add/update opencode provider
        echo "$EXISTING_AUTH" | ${pkgs.jq}/bin/jq --arg key "$DOPPLER_API_KEY" \
          '.opencode = {"type": "apiKey", "apiKey": $key}' \
          > "$OPENCODE_AUTH_FILE"
        
        chown havoc:staff "$OPENCODE_AUTH_FILE"
        chmod 600 "$OPENCODE_AUTH_FILE"
        echo "OpenCode Zen API key successfully injected to $OPENCODE_AUTH_FILE"
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
      "element"
      "obsidian"
      "plex"
      "plexamp"
      "proton-drive"
      "protonvpn"
      "proton-mail"
      "steam"
      "whisky"
    ];
    masApps = { };
  };
}
