{
  pkgs,
  lib,
  username,
  ...
}:
let
  llamaModelDownloader = pkgs.writeShellScript "llama-model-downloader" ''
    #!/usr/bin/env bash
    set -euo pipefail

    MODELS_DIR="$HOME/models"
    LOG="$MODELS_DIR/download.log"
    LOG_PREFIX="[llama-model-downloader]"

    log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $*" | tee -a "$LOG"; }

    mkdir -p "$MODELS_DIR"

    # 7B Q8 on all machines: fast enough for interactive pre-commit review (~15-30s per batch)
    MODEL_FILE="qwen2.5-coder-7b-instruct-q8_0.gguf"
    HF_REPO="bartowski/Qwen2.5-Coder-7B-Instruct-GGUF"
    HF_FILENAME="Qwen2.5-Coder-7B-Instruct-Q8_0.gguf"
    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
    TIER="7B Q8 (''${RAM_GB} GB device)"

    DEST="$MODELS_DIR/$MODEL_FILE"
    STAMP="$MODELS_DIR/.downloaded-$MODEL_FILE"

    if [ -f "$STAMP" ] && [ -f "$DEST" ]; then
      log "Model already present: $MODEL_FILE ($TIER) — skipping download"
      exit 0
    fi

    RESUME_FLAG=""
    if [ -f "$DEST" ]; then
      log "Partial download found, will attempt resume: $MODEL_FILE"
      RESUME_FLAG="-C -"
    fi

    log "Starting download: $MODEL_FILE ($TIER)"
    log "Source: https://huggingface.co/$HF_REPO/resolve/main/$HF_FILENAME"
    log "Destination: $DEST"

    if curl -fL ''${RESUME_FLAG} \
        --retry 5 --retry-delay 10 --retry-max-time 3600 \
        --connect-timeout 30 \
        -o "$DEST" \
        "https://huggingface.co/$HF_REPO/resolve/main/$HF_FILENAME" \
        >> "$LOG" 2>&1; then
      touch "$STAMP"
      log "Download complete: $MODEL_FILE"
    else
      log "ERROR: Download failed — see $LOG for details"
      rm -f "$DEST"
      exit 1
    fi
  '';

  llamaServerLauncher = pkgs.writeShellScript "llama-server-launcher" ''
    #!/usr/bin/env bash
    set -euo pipefail

    MODELS_DIR="$HOME/models"
    LOG_PREFIX="[llama-server-launcher]"

    log() { echo "$LOG_PREFIX $*"; }

    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
    log "Detected ''${RAM_GB} GB unified memory"
    MODEL_FILE="$MODELS_DIR/qwen2.5-coder-7b-instruct-q8_0.gguf"
    CTX_SIZE=32768
    TIER="7B Q8 (''${RAM_GB} GB device)"

    log "Selected tier: $TIER"
    log "Model file: $MODEL_FILE"

    if [ ! -f "$MODEL_FILE" ]; then
      log "ERROR: Model file not found: $MODEL_FILE"
      log "llama-server will NOT start until the model file is present."
      exit 1
    fi

    log "Starting llama-server..."
    exec /opt/homebrew/bin/llama-server \
      --model        "$MODEL_FILE" \
      --host         "127.0.0.1" \
      --port         "8080" \
      --ctx-size     "$CTX_SIZE" \
      --n-gpu-layers 99 \
      --flash-attn on \
      --cache-type-k q8_0 \
      --alias        "local-coder"
  '';

  llamaHealthChecker = pkgs.writeShellScript "llama-health-checker" ''
    #!/usr/bin/env bash
    set -euo pipefail

    SERVICE_NAME="org.nixos.llama-server"
    PLIST_PATH="$HOME/Library/LaunchAgents/$SERVICE_NAME.plist"
    HEALTH_URL="http://127.0.0.1:8080/health"
    LOG_PREFIX="[llama-health-checker]"

    log() { echo "$LOG_PREFIX $*"; }

    # Check if service is loaded in launchd
    if ! launchctl list "$SERVICE_NAME" &>/dev/null; then
      log "Service not loaded, attempting to load..."
      if [ -f "$PLIST_PATH" ]; then
        launchctl load "$PLIST_PATH" 2>&1 | sed "s/^/$LOG_PREFIX /"
        sleep 3
      else
        log "ERROR: Plist not found at $PLIST_PATH"
        log "Please rebuild nix-darwin configuration"
        exit 1
      fi
    fi

    # Check if server is responding
    if ! curl -sf "$HEALTH_URL" -o /dev/null --max-time 2 2>/dev/null; then
      log "Server not responding, restarting service..."
      launchctl kickstart -k "gui/$(id -u)/$SERVICE_NAME" 2>&1 | sed "s/^/$LOG_PREFIX /"
      
      # Wait for server to start (up to 30 seconds with progress indicator)
      log "Waiting for server to start (this may take 15-30 seconds)..."
      for i in {1..30}; do
        if curl -sf "$HEALTH_URL" -o /dev/null --max-time 2 2>/dev/null; then
          log "Server is now healthy (started in $i seconds)"
          exit 0
        fi
        if [ $((i % 5)) -eq 0 ]; then
          log "Still waiting... ($i/30 seconds)"
        fi
        sleep 1
      done
      
      log "ERROR: Server did not start within 30 seconds"
      log "Check /tmp/llama-server.log and /tmp/llama-server.error.log for details"
      exit 1
    else
      log "Server is healthy"
      exit 0
    fi
  '';

  openchamberLauncher = pkgs.writeShellScript "openchamber-launcher-wrapper" ''
    #!/usr/bin/env bash
    source "$HOME/.zshrc_envvars" 2>/dev/null || true

    # Add Homebrew to PATH for openchamber to find node
    export PATH="/opt/homebrew/bin:/opt/homebrew/opt/node@22/bin:$PATH"

    PASSWORD_FILE="$HOME/.config/openchamber/.ui-password"
    if [ ! -f "$PASSWORD_FILE" ] || [ ! -s "$PASSWORD_FILE" ]; then
      echo '[openchamber] ERROR: password file missing or empty at ~/.config/openchamber/.ui-password — refusing to start' >&2
      exit 1
    fi
    UI_PASSWORD=$(cat "$PASSWORD_FILE")
    export OPENCHAMBER_UI_PASSWORD="$UI_PASSWORD"

    # Use Homebrew openchamber if available, otherwise fall back to npm-installed version
    if [ -x "/opt/homebrew/bin/openchamber" ]; then
      exec /opt/homebrew/bin/openchamber --foreground --host 0.0.0.0 --port 3000
    elif [ -x "$HOME/.local/bin/openchamber" ]; then
      exec "$HOME/.local/bin/openchamber" --foreground --host 0.0.0.0 --port 3000
    else
      echo '[openchamber] ERROR: openchamber binary not found in /opt/homebrew/bin or ~/.local/bin' >&2
      exit 1
    fi
  '';

  aiselectWrapper = pkgs.writeShellScriptBin "aiselect" ''
    #!/usr/bin/env bash

    # Ensure llama-server is running before proceeding
    ${llamaHealthChecker} || {
      echo "Failed to start llama-server. Check /tmp/llama-server.log for details"
      exit 1
    }

    # Add your aiselect implementation here
    # For now, this is a placeholder that confirms llama-server is running
    echo "llama-server is running and healthy"
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
      "nikitabobko/tap"
      "warrensbox/tap"
      "Arthur-Ficial/tap"
      "xykong/tap"
      "slima4/claude-tui"
      "seunggabi/tap"
    ];
    brews = [
      "ansible"
      "ansible-lint"
      "atuin"
      "awscli"
      "bash-language-server"
      "btop"
      "cava"
      "cmake"
      "coreutils"
      "charmbracelet/tap/crush"
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
      "jq"
      "jsonlint"
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
      "llama.cpp"
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
      "nikitabobko/tap/aerospace"
      "alacritty"
      "balenaetcher"
      "betterdisplay"
      "claude"
      "claude-code"
      "xykong/tap/flux-markdown"
      "font-hack-nerd-font"
      "font-jetbrains-mono-nerd-font"
      "ghostty"
      "goland"
      "hyper"
      "insta360-link-controller"
      "jetbrains-toolbox"
      "keepingyouawake"
      "kitty"
      "krita"
      "lm-studio"
      "neovide-app"
      "plexamp"
      "proton-pass"
      "qmk-toolbox"
      "sf-symbols"
      "shottr"
      "sublime-text"
      "warrensbox/tap/tfswitch"
      "ungoogled-chromium"
      "vanilla"
      "via"
      "vial"
      "vlc"
      "zed"
      "zen"
    ];
    masApps = { };
    onActivation.cleanup = "zap";
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

  system.activationScripts.postUserActivation.text = lib.mkAfter ''

    mkdir -p "$HOME/models"
    mkdir -p "$HOME/Library/Logs/openchamber"
    (nohup ${llamaModelDownloader} </dev/null >>"$HOME/models/download.log" 2>&1 &)
    echo "[llama-model-downloader] Download check running in background — tail ~/models/download.log"

    if [ -f "$HOME/.config/opencode/opencode.json" ]; then
      echo "Patching opencode.json with correct home path..."
      ${pkgs.gnused}/bin/sed -i "s|__HOME__|$HOME|g" "$HOME/.config/opencode/opencode.json"
    fi

    # Symlink the Nix-store-built launcher into ~/.local/bin so both this path
    # and the launchd agent point to the same script — no duplication.
    mkdir -p "$HOME/.local/bin"
    ln -sf "${openchamberLauncher}" "$HOME/.local/bin/openchamber-launcher"

    (
      if ! command -v openchamber &>/dev/null; then
        echo "Installing openchamber..."
        # Use Node.js v22 from Homebrew for better-sqlite3 compatibility
        export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
        
        OPENCHAMBER_INSTALL_SCRIPT=$(mktemp)
        # Pinned to commit 3d548a3a526d8fe86fd76d5fef6426cb173b8e57 — update commit and checksum together when upgrading
        curl -fsSL https://raw.githubusercontent.com/openchamber/openchamber/3d548a3a526d8fe86fd76d5fef6426cb173b8e57/scripts/install.sh -o "$OPENCHAMBER_INSTALL_SCRIPT"
        # Pinned SHA-256 for the above commit — recompute with: shasum -a 256 install.sh
        EXPECTED_SHA256="aa268c96ddc6d7d53fc54d2e5c2312e689493ecef6ba4f69730a93d50cf33287"
        ACTUAL_SHA256="$(shasum -a 256 "$OPENCHAMBER_INSTALL_SCRIPT" | awk '{print $1}')"
        if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
          echo "ERROR: openchamber install script checksum mismatch — aborting" >&2
          rm -f "$OPENCHAMBER_INSTALL_SCRIPT"
          exit 1
        fi
        # Script is pinned by commit and checksum-verified above.
        # It installs the openchamber binary to ~/.local/bin — review the pinned
        # commit before bumping the version to confirm no new system modifications.
        bash "$OPENCHAMBER_INSTALL_SCRIPT"
        rm -f "$OPENCHAMBER_INSTALL_SCRIPT"
      fi
    ) || echo "WARNING: openchamber install failed — continuing activation" >&2

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

    (
      OPENCHAMBER_APP="/Applications/OpenChamber.app"
      if [ ! -d "$OPENCHAMBER_APP" ]; then
        echo "Installing OpenChamber desktop app..."
        # Pinned version — update OC_PINNED_VERSION and the arch-specific checksums together when upgrading.
        # Recompute checksums with: curl -fsSL <dmg-url> | shasum -a 256
        OC_PINNED_VERSION="v1.9.9"
        OC_VERSION_NUM="1.9.9"
        ARCH=$(uname -m)
        case "$ARCH" in
          x86_64) OC_ARCH="x86_64"; OC_PINNED_SHA256="ae73f8d11401bc2b87e112a51ba01ea9dab89e7fa4912f654300926cc255c58b" ;;
          arm64)  OC_ARCH="aarch64"; OC_PINNED_SHA256="1a45ea8d10462a80d2cd7a6c15d238c2c1efd62cd81a63e6128469894ae77826" ;;
          *)      echo "ERROR: Unsupported architecture: $ARCH" >&2; exit 1 ;;
        esac
        OPENCHAMBER_DMG_URL="https://github.com/openchamber/openchamber/releases/download/$OC_PINNED_VERSION/OpenChamber_''${OC_VERSION_NUM}_darwin-''${OC_ARCH}.dmg"
        echo "Downloading OpenChamber $OC_PINNED_VERSION ($OC_ARCH)..."
        OPENCHAMBER_TMPDIR=$(mktemp -d)
        curl -fsSL "$OPENCHAMBER_DMG_URL" -o "$OPENCHAMBER_TMPDIR/OpenChamber.dmg"
        OC_ACTUAL=$(shasum -a 256 "$OPENCHAMBER_TMPDIR/OpenChamber.dmg" | awk '{print $1}')
        if [ "$OC_ACTUAL" != "$OC_PINNED_SHA256" ]; then
          echo "ERROR: OpenChamber DMG checksum mismatch — aborting install" >&2
          rm -rf "$OPENCHAMBER_TMPDIR"
          exit 1
        fi
        MOUNT="$OPENCHAMBER_TMPDIR/mnt"
        mkdir -p "$MOUNT"
        hdiutil attach "$OPENCHAMBER_TMPDIR/OpenChamber.dmg" -nobrowse -mountpoint "$MOUNT" || { echo "ERROR: Failed to mount OpenChamber DMG" >&2; rm -rf "$OPENCHAMBER_TMPDIR"; exit 1; }
        [ -d "$MOUNT/OpenChamber.app" ] || { echo "ERROR: OpenChamber.app not found in mounted DMG at $MOUNT" >&2; hdiutil detach "$MOUNT" -quiet; rm -rf "$OPENCHAMBER_TMPDIR"; exit 1; }
        cp -R "$MOUNT/OpenChamber.app" /Applications/
        hdiutil detach "$MOUNT" -quiet
        rm -rf "$OPENCHAMBER_TMPDIR"
        echo "OpenChamber desktop app installed."
      fi
    ) || echo "WARNING: OpenChamber DMG install failed — continuing activation" >&2

  '';

  launchd.user.agents.openchamber = {
    serviceConfig = {
      # The wrapper script reads the password at runtime — never a static string in ps aux output.
      ProgramArguments = [
        "/bin/bash"
        "${openchamberLauncher}"
      ];
      KeepAlive = true;
      ThrottleInterval = 30;
      RunAtLoad = true;
      StandardOutPath = "/Users/${username}/Library/Logs/openchamber/openchamber.log";
      StandardErrorPath = "/Users/${username}/Library/Logs/openchamber/openchamber.error.log";
      LimitLoadToSessionType = [
        "Aqua"
        "Background"
        "LoginWindow"
        "StandardIO"
        "System"
      ];
    };
  };

  launchd.user.agents.llama-server = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "${llamaServerLauncher}"
      ];
      KeepAlive = true;
      RunAtLoad = true;
      StandardOutPath = "/tmp/llama-server.log";
      StandardErrorPath = "/tmp/llama-server.error.log";
      LimitLoadToSessionType = [
        "Aqua"
        "Background"
        "LoginWindow"
        "StandardIO"
        "System"
      ];
    };
  };

}
