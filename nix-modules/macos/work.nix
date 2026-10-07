{ pkgs, lib, ... }:
let
  wallpaper = "/Users/jrollet/.wallpapers/wallhaven-rr13w1.png";
in
{
  system.primaryUser = "jrollet";

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

    echo "Configuring kubectl for work environment..."
    USER_HOME="/Users/jrollet"
    KUBECONFIG_FILE="$USER_HOME/.kube/ps.config"
    ZSHRC_WORK="$USER_HOME/.zshrc_work"

    if [ -f "$KUBECONFIG_FILE" ]; then
      cat > "$ZSHRC_WORK" <<'EOF'
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
  # The claude-tui statusline on this profile shows only the context line. The monthly-cost budget bar is a local
  # estimate from session transcripts and did not match the usage page, so no budget is configured: with none,
  # format_monthly_cost() returns nothing and the compact line is just the context bar. The budget lives in
  # ~/.claude/claudeui.json (monthly_cost.budget), which nothing in this repo writes; drop it on every switch so a
  # hand-added one cannot bring the bar back. Only that one key is deleted (jq del keeps every other setting, and the
  # file is replaced atomically via mv); a file without the key is left untouched. Runs as the login user (activation
  # is root), non-fatal.
  system.activationScripts.postActivation.text = lib.mkAfter ''
    cfg=/Users/jrollet/.claude/claudeui.json
    jq_bin=${pkgs.jq}/bin/jq
    if [ ! -f "$cfg" ]; then
      echo "Statusline: $cfg does not exist, nothing to remove."
    elif ! sudo -u jrollet "$jq_bin" -e 'has("monthly_cost")' "$cfg" >/dev/null 2>&1; then
      echo "Statusline: $cfg has no monthly_cost (or is not valid JSON), leaving it as it is."
    elif sudo -u jrollet sh -c '"$1" "del(.monthly_cost)" "$2" > "$2.new" && mv "$2.new" "$2"' _ "$jq_bin" "$cfg"; then
      echo "Statusline: removed monthly_cost from $cfg (work statusline shows the context line only)."
    else
      echo "Warning: jq failed while removing monthly_cost from $cfg; the budget bar may still show." >&2
    fi
  '';

  networking.hostName = "MacBookM3Pro";
  networking.computerName = "MacBookM3Pro";

  # Makes plain gpc/gpa behave like gpc-local/gpa-local (local-only, no cloud
  # fallback) on this host by default -- see the guards at the top of
  # gpc()/gpa() in .zshrc_functions_git. Moved here from llamacpp-local.nix.
  # Does NOT affect aiselect or aidev/opencode. Override for one shell session
  # with `unset AI_LOCAL_DEFAULT`.
  environment.variables.AI_LOCAL_DEFAULT = "1";

  # Model and effort for aistack's Claude Code calls (claude-work.sh, claude-review.sh and the ralph agents in
  # aistack_func). Chosen per profile because work and personal use different Anthropic plans with different token
  # costs. Per-session override: export AISTACK_CLAUDE_MODEL / AISTACK_CLAUDE_EFFORT.
  environment.variables.AISTACK_CLAUDE_MODEL = "claude-opus-5-5";
  environment.variables.AISTACK_CLAUDE_EFFORT = "high";

  system.defaults = {
    dock.persistent-apps = [ ];
  };
  homebrew = {
    enable = true;
    taps = [ ];
    brews = [
      "act"
      "awscli"
      # Podman replaces Docker Desktop -- "docker" and "docker-compose" here are
      # the CLI-only formulae (distinct from the docker-desktop cask, which
      # bundled its own GUI/VM/daemon). Combined with `podman-mac-helper`
      # (installed manually once: `sudo podman-mac-helper install`, then a
      # `podman machine stop && podman machine start` cycle to activate it),
      # podman forwards the standard /var/run/docker.sock path, so this docker
      # CLI and any other docker-expecting tool work against it transparently
      # -- no DOCKER_HOST override needed.
      "podman"
      "docker"
      "docker-compose"
      "docker-credential-helper"
      "docker-credential-helper-ecr"
      "lazydocker"
    ];
    casks = [
      "citrix-workspace"
      "lastpass"
      "mqtt-explorer"
      "powershell"
      "remote-desktop-manager-free"
      "datagrip"
      "microsoft-365-copilot"
      "microsoft-excel"
      "microsoft-onenote"
      "microsoft-outlook"
      "microsoft-powerpoint"
      "microsoft-teams"
      "microsoft-word"
      "onedrive"
      "opcode"
      "rode-central"
      "slack"
      "teamviewer-host"
      "zoom"
    ];
    masApps = { };
  };

}
