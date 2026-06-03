# TUI/CLI packages shared across ALL profiles (laptop, desktop, work)
# GUI applications are in packages-gui.nix (laptop only)
{
  pkgs,
  lib,
  username,
  ...
}:
let
  # Remote llama-server configuration - connects to macminim1.rollet.family:8080
  llamaHealthChecker = pkgs.writeShellScript "llama-health-checker" ''
    #!/usr/bin/env bash
    set -euo pipefail

    # Use remote server for laptop/work configurations
    HEALTH_URL="http://macminim1.rollet.family:8080/health"
    LOG_PREFIX="[llama-health-checker]"

    log() { echo "$LOG_PREFIX $*"; }

    # Check if remote server is responding
    if ! curl -sf "$HEALTH_URL" -o /dev/null --max-time 5 2>/dev/null; then
      log "ERROR: Remote llama-server at macminim1.rollet.family:8080 is not responding"
      log "Please ensure the desktop machine is running and llama-server is active"
      exit 1
    else
      log "Remote llama-server is healthy"
      exit 0
    fi
  '';

  aiselectWrapper = pkgs.writeShellScriptBin "aiselect" ''
    #!/usr/bin/env bash

    # Ensure remote llama-server is accessible before proceeding
    ${llamaHealthChecker} || {
      echo "Failed to connect to remote llama-server at macminim1.rollet.family:8080"
      echo "Please ensure the desktop machine is running"
      exit 1
    }

    # Add your aiselect implementation here
    # For now, this is a placeholder that confirms llama-server is accessible
    echo "Remote llama-server at macminim1.rollet.family:8080 is running and healthy"
    echo "TODO: Implement actual aiselect functionality"
  '';

  claudeTuiSetup = pkgs.writeShellScript "claude-tui-setup" ''
        #!/usr/bin/env bash
        set -euo pipefail

        SETTINGS_FILE="$HOME/.claude/settings.json"
        COMMANDS_DIR="$HOME/.claude/commands"
        SETUP_MARKER="$HOME/.claude/.claudetui-configured"

        # Skip if already configured (marker file exists and settings are valid)
        if [ -f "$SETUP_MARKER" ] && [ -f "$SETTINGS_FILE" ]; then
          # Verify settings are still valid
          if grep -q '"statusLine"' "$SETTINGS_FILE" && \
             grep -q 'claudetui statusline' "$SETTINGS_FILE" && \
             [ -L "$COMMANDS_DIR/tui" ]; then
            echo "[claude-tui] Already configured, skipping setup"
            exit 0
          fi
        fi

        echo "[claude-tui] Configuring Claude Code integration..."

        # Ensure Claude Code directory exists
        if [ ! -d "$HOME/.claude" ]; then
          echo "[claude-tui] WARNING: ~/.claude directory not found — Claude Code may not be installed"
          exit 0
        fi

        # Ensure claudetui command is available
        if ! command -v claudetui &>/dev/null; then
          echo "[claude-tui] WARNING: claudetui command not found — installation may be incomplete"
          exit 0
        fi

        # Run setup with full mode (non-interactive)
        export STATUSLINE_MODE="full"
        export PATH="/opt/homebrew/bin:$PATH"
        
        # Create a temporary script to run setup non-interactively
        SETUP_SCRIPT=$(mktemp)
        cat > "$SETUP_SCRIPT" << 'SETUPEOF'
    #!/usr/bin/env bash
    set -euo pipefail

    SETTINGS_FILE="$HOME/.claude/settings.json"
    COMMANDS_DIR="$HOME/.claude/commands"
    INSTALL_DIR="''${INSTALL_DIR:-/opt/homebrew/opt/claude-tui/libexec}"

    # Configure settings.json
    python3 << 'PYEOF'
    import json
    import os
    from pathlib import Path

    settings_file = os.path.expanduser("~/.claude/settings.json")

    # Load or create settings
    settings = {}
    if os.path.exists(settings_file):
        try:
            with open(settings_file) as f:
                settings = json.load(f)
        except (json.JSONDecodeError, IOError):
            backup = settings_file + ".backup"
            if os.path.exists(settings_file):
                os.rename(settings_file, backup)

    # Configure statusline
    mode = os.environ.get("STATUSLINE_MODE", "full")
    statusline_cmd = "claudetui statusline"
    if mode == "compact":
        statusline_cmd += " --compact"

    settings["statusLine"] = {
        "type": "command",
        "command": statusline_cmd,
    }

    # Configure hooks
    hooks = settings.get("hooks", {})

    hook_configs = [
        {
            "event": "SessionStart",
            "matcher": "",
            "command": "claudetui hook session-heatmap",
        },
        {
            "event": "PreToolUse",
            "matcher": "Edit|Write",
            "command": "claudetui hook pre-edit-churn",
        },
        {
            "event": "PostToolUse",
            "matcher": "Edit|Write",
            "command": "claudetui hook post-edit-deps",
        },
    ]

    for cfg in hook_configs:
        event = cfg["event"]
        if event not in hooks:
            hooks[event] = []

        # Check if hook already exists
        already_exists = False
        for rule in hooks[event]:
            for h in rule.get("hooks", []):
                if h.get("command") == cfg["command"]:
                    already_exists = True
                    break
            if already_exists:
                break

        if not already_exists:
            hooks[event].append({
                "matcher": cfg["matcher"],
                "hooks": [{"type": "command", "command": cfg["command"]}],
            })

    settings["hooks"] = hooks

    # Write settings
    Path(settings_file).parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_file + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    os.replace(tmp, settings_file)
    PYEOF

    # Install slash commands
    mkdir -p "$COMMANDS_DIR"

    # Remove old symlink if present
    if [ -L "$COMMANDS_DIR/tui" ]; then
        rm "$COMMANDS_DIR/tui"
    fi

    # Create new symlink
    ln -sfn "$INSTALL_DIR/claude-code-commands/tui" "$COMMANDS_DIR/tui"

    echo "[claude-tui] Configuration complete"
    SETUPEOF

        chmod +x "$SETUP_SCRIPT"
        bash "$SETUP_SCRIPT"
        rm -f "$SETUP_SCRIPT"

        # Create marker file
        touch "$SETUP_MARKER"
        echo "[claude-tui] Setup completed successfully"
  '';
in
{
  environment.systemPackages = with pkgs; [
    nil
    nixd
    smassh
    python3Packages.fonttools
    lemminx
    rubyPackages.rubocop
    nodejs_22
    typescript
    aiselectWrapper
  ];

  homebrew = {
    enable = true;
    taps = [
      "warrensbox/tap"
      "xykong/tap"
      "slima4/claude-tui"
      "seunggabi/tap"
    ];
    brews = [
      "ansible"
      "ansible-lint"
      "argocd"
      "atuin"
      "bash-language-server"
      "btop"
      "cava"
      "cmake"
      "coreutils"
      "djlint"
      "dockerfile-language-server"
      "exiftool"
      "eza"
      "fastfetch"
      "fd"
      "fzf"
      "gh"
      "go"
      "golangci-lint"
      "golangci-lint-langserver"
      "gopls"
      "graphviz"
      "hadolint"
      "helm"
      "jq"
      "jsonlint"
      "k9s"
      "kubectl"
      "lazygit"
      "lua-language-server"
      "luarocks"
      "mas"
      "mpv"
      "neovide"
      "neovim"
      "nixfmt"
      "node@22"
      "opencode"
      "opentofu"
      "prettier"
      "python-lsp-server"
      "python3"
      "reattach-to-user-namespace"
      "ripgrep"
      "ruff"
      "rust"
      "rust-analyzer"
      "shfmt"
      "solargraph"
      "speedtest-cli"
      "sshpass"
      "starship"
      "stow"
      "stylua"
      "superfile"
      "syncthing"
      "taplo"
      "tealdeer"
      "telnet"
      "terraform-inventory"
      "terraform-ls"
      "terraform-lsp"
      "terraformer"
      "tflint"
      "tmux"
      "tpm"
      "tree-sitter"
      "typescript-language-server"
      "uv"
      "vscode-langservers-extracted"
      "watch"
      "yaml-language-server"
      "yamllint"
      "zoxide"
      "zplug"
      "ansible-language-server"
      "slima4/claude-tui/claude-tui"
    ];
    casks = [
      # CLI Tools
      "warrensbox/tap/tfswitch"
      "claude-code"

      # Fonts (shared by all profiles for terminal/TUI consistency)
      "font-hack-nerd-font"
      "font-jetbrains-mono-nerd-font"
    ];
    masApps = { };
    onActivation.cleanup = "zap";
    onActivation.extraFlags = [ "--force" ];
    onActivation.autoUpdate = true;
    onActivation.upgrade = true;
  };

  # Runs before brew bundle so Homebrew can link without conflict.
  system.activationScripts.homebrew.text = lib.mkBefore ''
    if [ -L /opt/homebrew/bin/jsonlint ] && readlink /opt/homebrew/bin/jsonlint | grep -q node_modules; then
      echo "Removing npm-installed jsonlint symlink (replaced by Homebrew)..."
      rm -f /opt/homebrew/bin/jsonlint
    fi
  '';

  system.activationScripts.packagesUserConfig.text = lib.mkAfter ''
        # Run user-specific package configuration as the primary user
        USER_NAME="$(id -un)"
        USER_HOME="$HOME"
        
        sudo -u "$USER_NAME" bash <<'USERSCRIPT'
        if [ -f "$HOME/.config/opencode/opencode.json" ]; then
          echo "Patching opencode.json with correct home path..."
          ${pkgs.gnused}/bin/sed -i "s|__HOME__|$HOME|g" "$HOME/.config/opencode/opencode.json"
        fi

        if ! command -v claude-dashboard &>/dev/null; then
          echo "Installing claude-dashboard..."
          brew install seunggabi/tap/claude-dashboard 2>&1 || true
        fi

        # Configure claude-tui for Claude Code
        (
          ${claudeTuiSetup}
        ) || echo "WARNING: claude-tui setup failed — continuing activation" >&2

        (
          OPCODE_APP="/Applications/opcode.app"
          if [ ! -d "$OPCODE_APP" ]; then
            echo "Installing Opcode desktop app..."
            # Pinned version — update OPCODE_PINNED_VERSION and OPCODE_PINNED_SHA256 together when upgrading.
            # Recompute checksum with: curl -fsSL <dmg-url> | shasum -a 256
            OPCODE_PINNED_VERSION="v0.2.0"
            OPCODE_PINNED_SHA256="9868d20b46fa3fba134049e931ef745571805b0e1919e7bad807ca454f5932f8"
            OPCODE_DMG_URL="https://github.com/winfunc/opcode/releases/download/$OPCODE_PINNED_VERSION/opcode_''${OPCODE_PINNED_VERSION}_macos_universal.dmg"
            echo "Downloading Opcode $OPCODE_PINNED_VERSION..."
            OPCODE_TMPDIR=$(mktemp -d)
            curl -fsSL "$OPCODE_DMG_URL" -o "$OPCODE_TMPDIR/opcode.dmg"
            OPCODE_ACTUAL=$(shasum -a 256 "$OPCODE_TMPDIR/opcode.dmg" | awk '{print $1}')
            if [ "$OPCODE_ACTUAL" != "$OPCODE_PINNED_SHA256" ]; then
              echo "ERROR: Opcode DMG checksum mismatch — aborting install" >&2
              rm -rf "$OPCODE_TMPDIR"
              exit 1
            fi
            MOUNT="$OPCODE_TMPDIR/mnt"
            mkdir -p "$MOUNT"
            hdiutil attach "$OPCODE_TMPDIR/opcode.dmg" -nobrowse -mountpoint "$MOUNT" || { echo "ERROR: Failed to mount Opcode DMG" >&2; rm -rf "$OPCODE_TMPDIR"; exit 1; }
            [ -d "$MOUNT/opcode.app" ] || { echo "ERROR: opcode.app not found in mounted DMG at $MOUNT" >&2; hdiutil detach "$MOUNT" -quiet; rm -rf "$OPCODE_TMPDIR"; exit 1; }
            cp -R "$MOUNT/opcode.app" /Applications/
            hdiutil detach "$MOUNT" -quiet
            rm -rf "$OPCODE_TMPDIR"
            echo "Opcode desktop app installed."
          fi
        ) || echo "WARNING: Opcode install failed — continuing activation" >&2
    USERSCRIPT
  '';

}
