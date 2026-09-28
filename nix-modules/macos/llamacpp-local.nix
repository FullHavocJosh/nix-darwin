{
  pkgs,
  lib,
  username,
  ...
}:
let
  llamaModelDownloader = pkgs.writeShellScript "llama-model-downloader-local" ''
    #!/usr/bin/env bash
    set -euo pipefail

    MODELS_DIR="$HOME/models"
    LOG="$MODELS_DIR/download.log"
    LOG_PREFIX="[llama-model-downloader-local]"

    log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $*" | tee -a "$LOG"; }

    mkdir -p "$MODELS_DIR"

    # Qwen 2.5 Coder 14B Q6_K for coding tasks (GPA/GPC functions), sized for
    # a 32GB laptop that also runs a normal daily app load -- leaves ~20GB
    # headroom rather than the ~20GB a 32B Q4 quant would consume outright.
    MODEL_FILE="qwen2.5-coder-14b-instruct-q6_k.gguf"
    HF_REPO="bartowski/Qwen2.5-Coder-14B-Instruct-GGUF"
    HF_FILENAME="Qwen2.5-Coder-14B-Instruct-Q6_K.gguf"
    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
    TIER="14B Q6_K (''${RAM_GB} GB device)"

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

  llamaServerLauncher = pkgs.writeShellScript "llama-server-local-launcher" ''
    #!/usr/bin/env bash
    set -euo pipefail

    MODELS_DIR="$HOME/models"
    LOG_PREFIX="[llama-server-local-launcher]"

    log() { echo "$LOG_PREFIX $*"; }

    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
    log "Detected ''${RAM_GB} GB unified memory"
    MODEL_FILE="$MODELS_DIR/qwen2.5-coder-14b-instruct-q6_k.gguf"
    # 32K matches the model's native training context, same reasoning as the
    # remote macminim1 server (llamacpp.nix) -- no RoPE scaling needed.
    CTX_SIZE=32768
    TIER="14B Q6_K (''${RAM_GB} GB device)"

    log "Selected tier: $TIER"
    log "Model file: $MODEL_FILE"

    if [ ! -f "$MODEL_FILE" ]; then
      log "ERROR: Model file not found: $MODEL_FILE"
      log "llama-server will NOT start until the model file is present."
      exit 1
    fi

    log "Starting local llama-server for coding (GPA/GPC functions)..."
    # Bound to loopback only -- unlike macminim1 (a stationary home server),
    # these are laptops that travel to untrusted networks, so this must never
    # be reachable off-host.
    exec llama-server \
      --model           "$MODEL_FILE" \
      --host            "127.0.0.1" \
      --port            "8080" \
      --ctx-size        "$CTX_SIZE" \
      --n-gpu-layers    99 \
      --flash-attn      on \
      --cache-type-k    q8_0 \
      --cache-type-v    q8_0 \
      --alias           "local-coder"
  '';
in
{
  environment.systemPackages = with pkgs; [
    llama-cpp
  ];

  environment.variables = {
    LLAMA_CPP_HOST = "http://localhost:8080";
    LLAMA_CPP_MODEL_LABEL = "Qwen2.5-Coder-14B";
  };

  system.activationScripts.llamacppLocalUserConfig.text = lib.mkAfter ''
    mkdir -p "$HOME/models"
    (nohup ${llamaModelDownloader} </dev/null >>"$HOME/models/download.log" 2>&1 &)
    echo "[llama-model-downloader-local] Download check running in background — tail ~/models/download.log"
  '';

  launchd.daemons.llama-server-local = {
    serviceConfig = {
      UserName = username;
      ProgramArguments = [
        "/bin/bash"
        "${llamaServerLauncher}"
      ];
      KeepAlive = true;
      RunAtLoad = true;
      StandardOutPath = "/tmp/llama-server-local.log";
      StandardErrorPath = "/tmp/llama-server-local.error.log";
    };
  };
}
