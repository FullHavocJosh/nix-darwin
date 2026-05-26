{ pkgs, ... }:
let
  wallpaper = "/Users/jrollet/.wallpapers/wallhaven-rr13w1.png";
in
{

  system.activationScripts.script.text = ''
            #!/usr/bin/env bash

            echo "Stowing dotfiles..."
            cd "/Users/jrollet/nix-darwin" || { echo "Failed to cd into /Users/jrollet/nix-darwin"; exit 1; }
            ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow dotfiles"; exit 1; }
            echo "Finished Stowing dotfiles..."

            if [ -f "$HOME/.config/opencode/opencode.json" ]; then
              echo "Patching opencode.json with correct home path..."
              ${pkgs.gnused}/bin/sed -i "s|__HOME__|$HOME|g" "$HOME/.config/opencode/opencode.json"
            fi

        # Configure kubectl for work profile only
        echo "Configuring kubectl for work environment..."
        USER_HOME="/Users/jrollet"
        KUBECONFIG_FILE="$USER_HOME/.kube/ps.config"
        ZSHRC_WORK="$USER_HOME/.zshrc_work"
        
        if [ -f "$KUBECONFIG_FILE" ]; then
          # Create/update .zshrc_work with kubectl configuration
          cat > "$ZSHRC_WORK" <<'EOF'
    # Work kubectl configuration - managed by nix-darwin
    export KUBECONFIG="$HOME/.kube/ps.config"
    export K9S_CONFIG_DIR="$HOME/.config/k9s"
    EOF
          chown jrollet:staff "$ZSHRC_WORK"
          chmod 644 "$ZSHRC_WORK"
          echo "kubectl configured for work environment in $ZSHRC_WORK"
        else
          echo "Warning: kubeconfig not found at $KUBECONFIG_FILE"
          echo "kubectl configuration will be skipped until $KUBECONFIG_FILE is available"
        fi

            echo "Setting wallpaper..."
            cp "${wallpaper}" "/Users/Shared/Wallpaper.png"
            cp "${wallpaper}" "/Users/Shared/psv_backgroundimage.png"
            osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "${wallpaper}"'
            killall WallpaperAgent 2>/dev/null || true
            killall Dock

            echo "Cleaning up Terraform cache files..."
            TERRAFORM_BASE="/Users/jrollet/pscloudops/terraform-infrastructure"

            # Count and show size before cleanup
            if [ -d "$TERRAFORM_BASE/v3" ] || [ -d "$TERRAFORM_BASE/v4" ]; then
              BEFORE_SIZE=$(find "$TERRAFORM_BASE/v3" "$TERRAFORM_BASE/v4" -type d -name ".terraform" -exec du -sk {} \; 2>/dev/null | awk '{sum+=$1} END {print sum/1024}')
              BEFORE_COUNT=$(find "$TERRAFORM_BASE/v3" "$TERRAFORM_BASE/v4" -type d -name ".terraform" 2>/dev/null | wc -l | tr -d ' ')

              if [ "$BEFORE_COUNT" -gt 0 ]; then
                echo "Found $BEFORE_COUNT .terraform directories (''${BEFORE_SIZE} MB)"

                find "$TERRAFORM_BASE/v3" "$TERRAFORM_BASE/v4" -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null

                echo "Cleaned up Terraform cache directories from v3 and v4"
              else
                echo "No .terraform directories found to clean"
              fi
            else
              echo "Terraform infrastructure directories (v3/v4) not found, skipping cleanup"
            fi
  '';
  networking.hostName = "MacBookProM3Pro";
  networking.computerName = "MacBookProM3Pro";

  system.defaults = {
    dock.persistent-apps = [ ];
  };
  homebrew = {
    enable = true;
    taps = [ ];
    brews = [
      "act"
    ];
    casks = [
      "citrix-workspace"
      "docker-desktop"
      "lastpass"
      "mqtt-explorer"
      "powershell"
      "remote-desktop-manager-free"
    ];
    masApps = { };
  };

}
