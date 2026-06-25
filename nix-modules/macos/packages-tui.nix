# TUI/CLI packages shared across ALL profiles (laptop, desktop, work)
# GUI applications are in packages-gui.nix (laptop only)
#
# PACKAGE POLICY: Prefer Homebrew for all new packages (brews/casks below).
# Only use environment.systemPackages for packages not available on Homebrew.
{
  pkgs,
  lib,
  username,
  ...
}:
let

  claudeTuiSetup = pkgs.writeShellScript "claude-tui-setup" ''
        #!/usr/bin/env bash
        set -euo pipefail

        SETTINGS_FILE="$HOME/.claude/settings.json"
        COMMANDS_DIR="$HOME/.claude/commands"
        SETUP_MARKER="$HOME/.claude/.claudetui-configured"

        if [ -f "$SETUP_MARKER" ] && [ -f "$SETTINGS_FILE" ]; then
          if grep -q '"statusLine"' "$SETTINGS_FILE" && \
             grep -q 'claudetui statusline' "$SETTINGS_FILE" && \
             [ -L "$COMMANDS_DIR/tui" ]; then
            echo "[claude-tui] Already configured, skipping setup"
            exit 0
          fi
        fi

        echo "[claude-tui] Configuring Claude Code integration..."

        if [ ! -d "$HOME/.claude" ]; then
          echo "[claude-tui] WARNING: ~/.claude directory not found — Claude Code may not be installed"
          exit 0
        fi

        if ! command -v claudetui &>/dev/null; then
          echo "[claude-tui] WARNING: claudetui command not found — installation may be incomplete"
          exit 0
        fi

        export STATUSLINE_MODE="full"
        export PATH="/opt/homebrew/bin:$PATH"
        SETUP_SCRIPT=$(mktemp)
        cat > "$SETUP_SCRIPT" << 'SETUPEOF'
    #!/usr/bin/env bash
    set -euo pipefail

    SETTINGS_FILE="$HOME/.claude/settings.json"
    COMMANDS_DIR="$HOME/.claude/commands"
    INSTALL_DIR="''${INSTALL_DIR:-/opt/homebrew/opt/claude-tui/libexec}"

    python3 << 'PYEOF'
    import json
    import os
    from pathlib import Path

    settings_file = os.path.expanduser("~/.claude/settings.json")

    settings = {}
    if os.path.exists(settings_file):
        try:
            with open(settings_file) as f:
                settings = json.load(f)
        except (json.JSONDecodeError, IOError):
            backup = settings_file + ".backup"
            if os.path.exists(settings_file):
                os.rename(settings_file, backup)

    mode = os.environ.get("STATUSLINE_MODE", "full")
    statusline_cmd = "claudetui statusline"
    if mode == "compact":
        statusline_cmd += " --compact"

    settings["statusLine"] = {
        "type": "command",
        "command": statusline_cmd,
    }

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

    Path(settings_file).parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_file + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    os.replace(tmp, settings_file)
    PYEOF

    mkdir -p "$COMMANDS_DIR"
    if [ -L "$COMMANDS_DIR/tui" ]; then
        rm "$COMMANDS_DIR/tui"
    fi
    ln -sfn "$INSTALL_DIR/claude-code-commands/tui" "$COMMANDS_DIR/tui"

    echo "[claude-tui] Configuration complete"
    SETUPEOF

        chmod +x "$SETUP_SCRIPT"
        bash "$SETUP_SCRIPT"
        rm -f "$SETUP_SCRIPT"

        touch "$SETUP_MARKER"
        echo "[claude-tui] Setup completed successfully"
  '';
in
{
  # Packages not available on Homebrew — add here only as a last resort.
  environment.systemPackages = with pkgs; [
    nil
    nixd
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
      "typescript"
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
      "warrensbox/tap/tfswitch"
      "claude-code"
      "font-hack-nerd-font"
      "font-jetbrains-mono-nerd-font"
    ];
    masApps = { };
    onActivation.cleanup = "none";
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
