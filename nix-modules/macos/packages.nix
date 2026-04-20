{ pkgs, lib, ... }:
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
in
{
  environment.systemPackages = with pkgs; [
    nil
    nixd
    smassh
    python3Packages.fonttools
    lemminx
    rubyPackages.rubocop
    openvpn
    nodejs_22
    typescript
    aiselectWrapper
  ];

  homebrew = {
    enable = true;
    taps = [
      "nikitabobko/tap"
      "charmbracelet/tap"
      "warrensbox/tap"
      "Arthur-Ficial/tap"
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
      "kubectl"
      "lazygit"
      "lua-language-server"
      "luarocks"
      "mas"
      "mpv"
      "neovide"
      "neovim"
      "nixfmt"
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
    ];
    casks = [
      "nikitabobko/tap/aerospace"
      "alacritty"
      "balenaetcher"
      "betterdisplay"
      "claude"
      "claude-code"
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

  system.activationScripts.postUserActivation.text = lib.mkAfter ''
    mkdir -p "$HOME/models"
    (nohup ${llamaModelDownloader} </dev/null >>"$HOME/models/download.log" 2>&1 &)
    echo "[llama-model-downloader] Download check running in background — tail ~/models/download.log"

    if [ -f "$HOME/.config/opencode/opencode.json" ]; then
      echo "Patching opencode.json with correct home path..."
      ${pkgs.gnused}/bin/sed -i "s|__HOME__|$HOME|g" "$HOME/.config/opencode/opencode.json"
    fi

  '';

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

