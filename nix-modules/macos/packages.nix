{ pkgs, lib, ... }:
let
  # =============================================================================
  # llama-server launcher — RAM-aware model selection
  # =============================================================================
  #
  # Reads hw.memsize at service-start time and selects the largest Qwen2.5-Coder
  # model that fits comfortably in unified memory, leaving ~8–17 GB for the OS.
  #
  # Tiers (all use --alias local-coder so shell code never needs to know RAM):
  #   < 24 GB  →  qwen2.5-coder-7b-instruct-q8_0.gguf   (~8 GB,  M1 16 GB)
  #   24–30 GB →  qwen2.5-coder-14b-instruct-q8_0.gguf  (~15 GB, M2 Pro 32 GB)
  #   > 30 GB  →  qwen2.5-coder-32b-instruct-q4_k_m.gguf (~19 GB, M3 Pro 36 GB)
  #
  # Models are downloaded automatically on first darwin-rebuild switch via
  # llamaModelDownloader (postUserActivation). The download runs in the
  # background so it does not block the rebuild.
  #

  # =============================================================================
  # llama-model-downloader — triggered by postUserActivation
  # =============================================================================
  #
  # Detects RAM tier, checks if the model file already exists, and if not,
  # downloads it from HuggingFace in the background (non-blocking).
  # A stamp file at ~/models/.downloaded-<filename> prevents re-downloading.
  #
  llamaModelDownloader = pkgs.writeShellScript "llama-model-downloader" ''
    #!/usr/bin/env bash
    set -euo pipefail

    MODELS_DIR="$HOME/models"
    LOG="$MODELS_DIR/download.log"
    LOG_PREFIX="[llama-model-downloader]"

    log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $*" | tee -a "$LOG"; }

    mkdir -p "$MODELS_DIR"

    # ── Model selection ────────────────────────────────────────────────────────
    # 7B Q8 on all machines: fast enough for interactive pre-commit review
    # (~15-30s per batch). Larger models (14B/32B) are too slow for gpa.
    MODEL_FILE="qwen2.5-coder-7b-instruct-q8_0.gguf"
    HF_REPO="bartowski/Qwen2.5-Coder-7B-Instruct-GGUF"
    HF_FILENAME="Qwen2.5-Coder-7B-Instruct-Q8_0.gguf"
    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
    TIER="7B Q8 (''${RAM_GB} GB device)"

    DEST="$MODELS_DIR/$MODEL_FILE"
    STAMP="$MODELS_DIR/.downloaded-$MODEL_FILE"

    # ── Already present — nothing to do ───────────────────────────────────────
    if [ -f "$STAMP" ] && [ -f "$DEST" ]; then
      log "Model already present: $MODEL_FILE ($TIER) — skipping download"
      exit 0
    fi

    # ── Partial download present — resume it ──────────────────────────────────
    RESUME_FLAG=""
    if [ -f "$DEST" ]; then
      log "Partial download found, will attempt resume: $MODEL_FILE"
      RESUME_FLAG="-C -"
    fi

    log "Starting download: $MODEL_FILE ($TIER)"
    log "Source: https://huggingface.co/$HF_REPO/resolve/main/$HF_FILENAME"
    log "Destination: $DEST"

    # curl: -L follow redirects, -f fail on HTTP errors, --retry 5 on transient failures
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
      # Remove incomplete file so next run tries again cleanly
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

    # ── Model selection ────────────────────────────────────────────────────────
    # 7B Q8 on all machines: fast enough for interactive pre-commit review.
    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
    log "Detected ''${RAM_GB} GB unified memory"
    MODEL_FILE="$MODELS_DIR/qwen2.5-coder-7b-instruct-q8_0.gguf"
    CTX_SIZE=32768
    TIER="7B Q8 (''${RAM_GB} GB device)"

    log "Selected tier: $TIER"
    log "Model file: $MODEL_FILE"

    # ── Verify model file exists ───────────────────────────────────────────────
    if [ ! -f "$MODEL_FILE" ]; then
      log "ERROR: Model file not found: $MODEL_FILE"
      log "Download it with:"
      log "  huggingface-cli download Qwen/Qwen2.5-Coder-32B-Instruct-GGUF \\"
      log "    --include \"qwen2.5-coder-32b-instruct-q4_k_m*.gguf\" --local-dir ~/models/"
      log "llama-server will NOT start until the model file is present."
      exit 1
    fi

    # ── Launch llama-server ────────────────────────────────────────────────────
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
in
{
  environment.systemPackages = with pkgs; [
    nil
    nixd # Nix language server
    smassh
    python3Packages.fonttools # For creating font aliases
    lemminx # XML Language Server
    rubyPackages.rubocop # Ruby linter/formatter
    openvpn # OpenVPN client for VPN connections
    nodejs_22 # Node.js for MCP servers and development
    typescript # TypeScript compiler
  ];

  homebrew = {
    enable = true;
    taps = [
      "warrensbox/tap"
      "nikitabobko/tap"
      "charmbracelet/tap"
      "dimentium/autoraise"
      "felixkratz/formulae"
    ];
    brews = [
      "ansible"
      "ansible-lint"
      "atuin"
      "dimentium/autoraise/autoraise"
      "awscli"
      "bash-language-server"
      "felixkratz/formulae/borders"
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
      "opencode" # OpenCode CLI - now available in homebrew
      "llama.cpp" # llama.cpp - local LLM inference server for gpa/gpc/gpr
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
      "warrensbox/tap/tfswitch"
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
      "kitty"
      "krita"
      "librewolf"
      "lm-studio"
      "neovide-app"
      "plexamp"
      "proton-pass"
      "qmk-toolbox"
      "sf-symbols"
      "shottr"
      "stats"
      "sublime-text"
      "ungoogled-chromium"
      "vanilla"
      "via"
      "vial"
      "vlc"
      "zed"
      "zen"
    ];
    masApps = {
      "Xcode" = 497799835;
    };
    onActivation.cleanup = "zap";
    onActivation.autoUpdate = true;
    onActivation.upgrade = true;
  };

  # Download the correct llama model for this machine's RAM tier on every
  # darwin-rebuild switch. The downloader is idempotent (stamp file check)
  # and runs in the background so it never blocks the rebuild.
  #
  # Must use postUserActivation (not a named key or postActivation) because only
  # postUserActivation runs as the logged-in user — named keys run as root.
  # lib.mkAfter appends to the existing postUserActivation.text in config.nix.
  system.activationScripts.postUserActivation.text = lib.mkAfter ''
    # Trigger llama model download for this machine's RAM tier (non-blocking)
    mkdir -p "$HOME/models"
    (nohup ${llamaModelDownloader} </dev/null >>"$HOME/models/download.log" 2>&1 &)
    echo "[llama-model-downloader] Download check running in background — tail ~/models/download.log"
  '';

  # llama-server launchd agent — shared across personal and work configs
  # The wrapper script selects the model at startup based on available RAM.
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

  # Borders - window border highlighter for AeroSpace
  launchd.user.agents.borders = {
    serviceConfig = {
      ProgramArguments = [
        "/opt/homebrew/bin/borders"
        "width=8.0"
        "hidpi=on"
        "active_color=glow(0xFFCBA6F7)"
      ];
      KeepAlive = true;
      RunAtLoad = true;
      StandardOutPath = "/tmp/borders.log";
      StandardErrorPath = "/tmp/borders.error.log";
      LimitLoadToSessionType = "Aqua";
    };
  };

  # AutoRaise - automatically raise windows on hover

}
