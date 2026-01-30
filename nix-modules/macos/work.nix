{ pkgs, config, ... }:
{

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

    echo "Cleaning up Terraform cache files..."
    TERRAFORM_BASE="/Users/jrollet/pscloudops/terraform-infrastructure"

    # Count and show size before cleanup
    if [ -d "$TERRAFORM_BASE/v3" ] || [ -d "$TERRAFORM_BASE/v4" ]; then
      BEFORE_SIZE=$(find "$TERRAFORM_BASE/v3" "$TERRAFORM_BASE/v4" -type d -name ".terraform" -exec du -sk {} \; 2>/dev/null | awk '{sum+=$1} END {print sum/1024}')
      BEFORE_COUNT=$(find "$TERRAFORM_BASE/v3" "$TERRAFORM_BASE/v4" -type d -name ".terraform" 2>/dev/null | wc -l | tr -d ' ')
      
      if [ "$BEFORE_COUNT" -gt 0 ]; then
        echo "Found $BEFORE_COUNT .terraform directories (''${BEFORE_SIZE} MB)"
        
        # Remove .terraform directories from v3 and v4 only
        find "$TERRAFORM_BASE/v3" "$TERRAFORM_BASE/v4" -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null
        
        # Also remove .terraform.lock.hcl files
        find "$TERRAFORM_BASE/v3" "$TERRAFORM_BASE/v4" -type f -name ".terraform.lock.hcl" -delete 2>/dev/null
        
        echo "Cleaned up Terraform cache files from v3 and v4 directories"
      else
        echo "No .terraform directories found to clean"
      fi
    else
      echo "Terraform infrastructure directories (v3/v4) not found, skipping cleanup"
    fi
  '';
  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    # Apps installed via nix package must include ${pkgs.APPNAME}
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
