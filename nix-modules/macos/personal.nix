{ pkgs, ... }:
let
  wallpaper = "/Users/havoc/.wallpapers/wallhaven-5yk6k9.jpg";
in
{
  system.primaryUser = "havoc";

  system.activationScripts.script.text = ''
    #!/usr/bin/env bash
    echo "Stowing dotfiles as user $(whoami)..."
    cd "/Users/havoc/nix-darwin" || { echo "Failed to cd into /Users/havoc/nix-darwin"; exit 1; }
    ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow dotfiles"; exit 1; }
    echo "Finished Stowing dotfiles..."

    echo "Setting wallpaper..."
    launchctl asuser "$(id -u -- havoc)" osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "${wallpaper}"' 2>/dev/null || \
      echo "Wallpaper: System Events not yet running, will apply on next login."

    # Configure kubectl for personal devices only
    echo "Configuring kubectl for hetzner-cluster..."
    USER_HOME="/Users/havoc"
    KUBECONFIG_FILE="$USER_HOME/home-infrastructure/hetzner-k3s/kubeconfig"
    ZSHRC_PERSONAL="$USER_HOME/.zshrc_personal"

    if [ -f "$KUBECONFIG_FILE" ]; then
      cat > "$ZSHRC_PERSONAL" <<'EOF'
    export KUBECONFIG="$HOME/home-infrastructure/hetzner-k3s/kubeconfig"
    export K9S_CONFIG_DIR="$HOME/.config/k9s"
    if command -v kubectl &>/dev/null && [ -f "$KUBECONFIG" ]; then
      kubectl config use-context hetzner-cluster-master1 &>/dev/null
    fi
    EOF
      chown havoc:staff "$ZSHRC_PERSONAL"
      chmod 644 "$ZSHRC_PERSONAL"
      echo "kubectl configured for hetzner-cluster-master1 in $ZSHRC_PERSONAL"
    else
      echo "Warning: kubeconfig not found at $KUBECONFIG_FILE"
    fi

    # Doppler auth is per-user; activation runs as root, so secrets are fetched via sudo -u havoc
    echo "Fetching OpenCode Zen API key from Doppler..."
    USER_HOME="/Users/havoc"
    OPENCODE_DATA_DIR="$USER_HOME/.local/share/opencode"
    OPENCODE_AUTH_FILE="$OPENCODE_DATA_DIR/auth.json"
    DOPPLER_BIN="/opt/homebrew/bin/doppler"
    DOPPLER_CONFIG="$USER_HOME/.doppler/.doppler.yaml"

    if [ -x "$DOPPLER_BIN" ] && [ -f "$DOPPLER_CONFIG" ]; then
      mkdir -p "$OPENCODE_DATA_DIR"
      # MacBookM2Pro -> root_macbook, MacMiniM1 -> root_macmini
      HOSTNAME=$(scutil --get LocalHostName)
      case "$HOSTNAME" in
        MacBookM2Pro*)
          DOPPLER_CONFIG_NAME="root_macbook"
          ;;
        MacMiniM1*)
          DOPPLER_CONFIG_NAME="root_macmini"
          ;;
        *)
          echo "Warning: Unknown hostname '$HOSTNAME'. Cannot determine Doppler config."
          DOPPLER_CONFIG_NAME=""
          ;;
      esac
      
      if [ -z "$DOPPLER_CONFIG_NAME" ]; then
        echo "Skipping OpenCode Zen API key injection due to unknown hostname."
      else
        echo "Using Doppler config: $DOPPLER_CONFIG_NAME for hostname: $HOSTNAME"
        
        DOPPLER_API_KEY=$(sudo -u havoc HOME="$USER_HOME" "$DOPPLER_BIN" secrets get OPENCODE_ZEN_API_KEY --project FullHavocJosh --config "$DOPPLER_CONFIG_NAME" --plain 2>/dev/null)

        if [ -n "$DOPPLER_API_KEY" ]; then
          if [ -f "$OPENCODE_AUTH_FILE" ]; then
            EXISTING_AUTH=$(cat "$OPENCODE_AUTH_FILE")
          else
            EXISTING_AUTH="{}"
          fi
          
          # "key" not "apiKey" — OpenCode CLI format requires this exact field name
          echo "$EXISTING_AUTH" | ${pkgs.jq}/bin/jq --arg key "$DOPPLER_API_KEY" \
            '.opencode = {"type": "api", "key": $key}' \
            > "$OPENCODE_AUTH_FILE"
          
          chown havoc:staff "$OPENCODE_AUTH_FILE"
          chmod 600 "$OPENCODE_AUTH_FILE"
          echo "OpenCode Zen API key successfully injected to $OPENCODE_AUTH_FILE"
        else
          echo "Warning: Failed to fetch OPENCODE_ZEN_API_KEY from Doppler."
          echo "Make sure you're authenticated with: doppler login"
          echo "And verify the secret exists in project 'FullHavocJosh', config '$DOPPLER_CONFIG_NAME'"
        fi
      fi
    else
      echo "Warning: Doppler CLI not found at $DOPPLER_BIN or config missing. OpenCode Zen API key not injected."
    fi

  '';

  launchd.daemons.ollama = {
    serviceConfig = {
      ProgramArguments = [
        "/Applications/Ollama.app/Contents/Resources/ollama"
        "serve"
      ];
      EnvironmentVariables = {
        OLLAMA_HOST = "0.0.0.0:11434";
        OLLAMA_FLASH_ATTENTION = "1";
        OLLAMA_KV_CACHE_TYPE = "q8_0";
        HOME = "/Users/havoc";
      };
      UserName = "havoc";
      KeepAlive = true;
      RunAtLoad = true;
      StandardOutPath = "/tmp/ollama.log";
      StandardErrorPath = "/tmp/ollama.error.log";
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
      "minio/stable/mc"
      "tailscale"
      "vitobotta/tap/hetzner_k3s"
    ];
    casks = [
      "element"
      "font-merriweather"
      "font-open-sans"
      "obsidian"
      "plex"
      "plexamp"
      "proton-drive"
      "protonvpn"
      "proton-mail"
    ];
    masApps = { };
  };
}
