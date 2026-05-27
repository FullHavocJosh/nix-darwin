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

    # Qwen 2.5 Coder 7B Q8 for coding tasks (GPA/GPC functions)
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
    # Context size: 96K with Q4_0 cache for 16GB RAM (model=7.5GB + ctx=6GB + system=2.5GB)
    # Q4_0 KV cache uses half the memory of Q8_0, allowing 2x context size
    # 96K effective context with RoPE scaling supports large codebases and long conversations
    CTX_SIZE=98304
    TIER="7B Q8 (''${RAM_GB} GB device)"

    log "Selected tier: $TIER"
    log "Model file: $MODEL_FILE"

    if [ ! -f "$MODEL_FILE" ]; then
      log "ERROR: Model file not found: $MODEL_FILE"
      log "llama-server will NOT start until the model file is present."
      exit 1
    fi

    log "Starting llama-server for coding (GPA/GPC functions)..."
    exec /opt/homebrew/bin/llama-server \
      --model           "$MODEL_FILE" \
      --host            "0.0.0.0" \
      --port            "8080" \
      --ctx-size        "$CTX_SIZE" \
      --override-kv     "llama.context_length=int:131072" \
      --rope-scaling    linear \
      --rope-freq-scale 0.666667 \
      --n-gpu-layers    99 \
      --flash-attn      on \
      --cache-type-k    q4_0 \
      --alias           "local-coder"
  '';
in
{
  homebrew.brews = [
    "llama.cpp"
  ];

  system.activationScripts.llamacppUserConfig.text = lib.mkAfter ''
    mkdir -p "$HOME/models"
    (nohup ${llamaModelDownloader} </dev/null >>"$HOME/models/download.log" 2>&1 &)
    echo "[llama-model-downloader] Download check running in background — tail ~/models/download.log"
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
