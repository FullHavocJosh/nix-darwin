{
  pkgs,
  lib,
  username,
  ...
}:
let
  # Every locally-servable model. `id` is the stable key written to
  # ~/.config/llama-cpp/selected-model by aiselect and matched in the
  # launcher's case statement below -- keep it slug-safe (no spaces/slashes).
  # All models share one llama-server alias ("local-coder"), so nothing
  # elsewhere in .zshrc_functions_ai/_git needs to know which one is loaded;
  # only the display label (_llamacpp_model_short) reads this state file.
  localModels = [
    {
      id = "qwen2.5-coder-14b";
      label = "Qwen2.5-Coder-14B";
      hfRepo = "bartowski/Qwen2.5-Coder-14B-Instruct-GGUF";
      hfFilename = "Qwen2.5-Coder-14B-Instruct-Q6_K.gguf";
      localFilename = "qwen2.5-coder-14b-instruct-q6_k.gguf";
      ctxSize = 32768;
      note = "coding-specialized, ~12GB (Q6_K)";
    }
    {
      id = "gemma-4-26b-a4b";
      label = "Gemma-4-26B-A4B";
      hfRepo = "bartowski/google_gemma-4-26B-A4B-it-GGUF";
      hfFilename = "google_gemma-4-26B-A4B-it-Q4_K_M.gguf";
      localFilename = "gemma-4-26b-a4b-it-q4_k_m.gguf";
      ctxSize = 32768;
      note = "MoE, general + coding, ~17GB (Q4_K_M)";
    }
  ];

  defaultModelId = (builtins.head localModels).id;

  downloadBlock = m: ''
    MODEL_FILE="${m.localFilename}"
    HF_REPO="${m.hfRepo}"
    HF_FILENAME="${m.hfFilename}"
    DEST="$MODELS_DIR/$MODEL_FILE"
    STAMP="$MODELS_DIR/.downloaded-$MODEL_FILE"

    if [ -f "$STAMP" ] && [ -f "$DEST" ]; then
      log "Model already present: $MODEL_FILE (${m.label}) — skipping download"
    else
      RESUME_FLAG=""
      if [ -f "$DEST" ]; then
        log "Partial download found, will attempt resume: $MODEL_FILE"
        RESUME_FLAG="-C -"
      fi

      log "Starting download: $MODEL_FILE (${m.label})"
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
        log "ERROR: Download failed for $MODEL_FILE — see $LOG for details"
        rm -f "$DEST"
      fi
    fi
  '';

  llamaModelDownloader = pkgs.writeShellScript "llama-model-downloader-local" ''
    #!/usr/bin/env bash
    set -uo pipefail

    MODELS_DIR="$HOME/models"
    LOG="$MODELS_DIR/download.log"
    LOG_PREFIX="[llama-model-downloader-local]"

    log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $*" | tee -a "$LOG"; }

    mkdir -p "$MODELS_DIR"

    ${lib.concatMapStringsSep "\n" downloadBlock localModels}
  '';

  launcherCaseBlock = m: ''
      ${m.id})
        MODEL_FILE="$MODELS_DIR/${m.localFilename}"
        CTX_SIZE=${toString m.ctxSize}
        LABEL="${m.label}"
        ;;
  '';

  llamaServerLauncher = pkgs.writeShellScript "llama-server-local-launcher" ''
    #!/usr/bin/env bash
    set -euo pipefail

    MODELS_DIR="$HOME/models"
    STATE_FILE="$HOME/.config/llama-cpp/selected-model"
    LOG_PREFIX="[llama-server-local-launcher]"

    log() { echo "$LOG_PREFIX $*"; }

    SELECTED="${defaultModelId}"
    if [ -f "$STATE_FILE" ]; then
      CANDIDATE="$(cat "$STATE_FILE")"
      case "$CANDIDATE" in
        ${lib.concatMapStringsSep "|" (m: m.id) localModels})
          SELECTED="$CANDIDATE"
          ;;
        *)
          log "WARNING: unknown selected-model '$CANDIDATE', falling back to ${defaultModelId}"
          ;;
      esac
    fi

    MODEL_FILE=""
    CTX_SIZE=32768
    LABEL=""
    case "$SELECTED" in
    ${lib.concatMapStringsSep "" launcherCaseBlock localModels}
    esac

    log "Selected model: $SELECTED ($LABEL)"
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
    LLAMA_CPP_MODEL_LABEL = "${(builtins.head localModels).label}";
    # Makes plain gpc/gpa behave like gpc-local/gpa-local (local-only, no
    # cloud fallback) on this host by default -- see the guards at the top
    # of gpc()/gpa() in .zshrc_functions_git. Does NOT affect aiselect or
    # aidev/opencode, which still resolve the provider normally, so llama-cpp
    # stays a free choice there rather than a forced one. Override for a
    # single shell session with `unset AI_LOCAL_DEFAULT`.
    AI_LOCAL_DEFAULT = "1";
  };

  # system.activationScripts run as root, so plain $HOME resolves to /var/root
  # -- not the laptop's actual user -- and the background downloader would
  # silently write nowhere the launchd agent (which does run as `username`)
  # can ever find. sudo --set-home -u is the pattern config.nix already uses
  # for the same problem (see its homebrew/script activation scripts).
  system.activationScripts.llamacppLocalUserConfig.text = lib.mkAfter ''
    sudo --set-home -u ${username} bash <<'USERSCRIPT'
    mkdir -p "$HOME/models"
    mkdir -p "$HOME/.config/llama-cpp"
    if [ ! -f "$HOME/.config/llama-cpp/selected-model" ]; then
      echo "${defaultModelId}" > "$HOME/.config/llama-cpp/selected-model"
    fi
    nohup ${llamaModelDownloader} </dev/null >>"$HOME/models/download.log" 2>&1 &
    disown
    echo "[llama-model-downloader-local] Download check running in background — tail ~/models/download.log"
    USERSCRIPT
  '';

  # A per-user LaunchAgent (not a system LaunchDaemon) so aiselect can
  # restart it with `launchctl kickstart -k gui/$(id -u)/org.nixos.llama-server-local`
  # to switch models, without needing sudo each time.
  launchd.user.agents.llama-server-local = {
    serviceConfig = {
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
