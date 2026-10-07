{
  lib,
  pkgs,
  username,
  ...
}:
let
  # The one local model, on every host (personal and work, laptops and desktop).
  # gpc/gpa/gpr (aider), aistack's pi planner and opencode all call this alias.
  # Fixed, not picked by RAM: on a ~30k-token prompt the 27B prefilled at 47 tok/s
  # on the M2 Pro vs 156 tok/s for the 9B (measured 2026-10-05 on LM Studio).
  modelAlias = "qwen/qwen3.5-9b";

  model = {
    # Same publisher as the MLX build LM Studio used; llama.cpp cannot load MLX,
    # so this is the GGUF of the same checkpoint. Size and sha256 are the values
    # Hugging Face reports for the file (2026-10-07).
    hfRepo = "lmstudio-community/Qwen3.5-9B-GGUF";
    file = "Qwen3.5-9B-Q4_K_M.gguf";
    sizeBytes = 5627044256;
    sha256 = "cd76ec205963b3b33350093e6904d9de16c4e666fd104e1f632d25c7f15f2a13";
  };

  # Never changes: the server is bound to loopback only, on every host, and the
  # port is not configurable per host. See the launcher comment.
  bindHost = "127.0.0.1";
  port = 8080;

  # Context window. One slot (--parallel 1) gets all of it.
  ctxSize = 131072;

  modelDownloader = pkgs.writeShellScript "llama-model-downloader-local" ''
    #!/usr/bin/env bash
    set -uo pipefail

    MODELS_DIR="$HOME/models"
    LOG="$MODELS_DIR/download.log"
    LOG_PREFIX="[llama-model-downloader-local]"
    DEST="$MODELS_DIR/${model.file}"

    mkdir -p "$MODELS_DIR"
    log() {
      local line
      line="$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $*"
      if [ -t 1 ]; then echo "$line" | tee -a "$LOG"; else echo "$line" >> "$LOG"; fi
    }

    verify() {
      [ -f "$DEST" ] && [ "$(/usr/bin/shasum -a 256 "$DEST" | cut -d' ' -f1)" = "${model.sha256}" ]
    }

    # Hashing 5.6GB takes a few seconds; only do it when the size already matches.
    SIZE=$(stat -f %z "$DEST" 2>/dev/null || echo 0)
    if [ "$SIZE" = "${toString model.sizeBytes}" ] && verify; then
      log "${model.file}: present and verified -- skipping"
      exit 0
    fi

    log "${model.file}: downloading from ${model.hfRepo} (resumes a partial file)"
    if ! ${pkgs.curl}/bin/curl -fL -C - --retry 5 --retry-delay 10 --retry-max-time 3600 \
        --connect-timeout 30 -o "$DEST" \
        "https://huggingface.co/${model.hfRepo}/resolve/main/${model.file}" >> "$LOG" 2>&1; then
      log "ERROR: download failed -- see $LOG"
      exit 1
    fi
    if verify; then
      log "${model.file}: download complete, sha256 verified"
    else
      log "ERROR: ${model.file}: sha256 mismatch -- removing it"
      rm -f "$DEST"
      exit 1
    fi
  '';

  serverLauncher = pkgs.writeShellScript "llama-server-local-launcher" ''
    #!/usr/bin/env bash
    set -euo pipefail

    MODEL_FILE="$HOME/models/${model.file}"
    if [ ! -f "$MODEL_FILE" ]; then
      echo "[llama-server-local-launcher] ERROR: $MODEL_FILE not found; the downloader runs on darwin-rebuild (tail ~/models/download.log)" >&2
      exit 1
    fi

    # Loopback only, hard-coded: no flag, variable or per-host option changes it.
    # Nothing off this machine can reach the model, and this machine's tools never
    # call another machine's model (the only remote LLM is Lumo, over HTTP).
    #
    # --parallel 1: llama-server defaults to 4 slots and divides --ctx-size across
    # them; one aider/pi conversation needs the whole window in one slot.
    #
    # --cache-type-k q8_0 / --cache-type-v q4_0: smaller KV cache at large context.
    #
    # --jinja: the model's own chat template, needed for tool calls (pi, opencode).
    # Thinking stays on by default (pi/aistack want it; the server splits it into
    # reasoning_content). One-shot callers (aider: commit messages, reviews) turn
    # it off per request with chat_template_kwargs.enable_thinking=false -- tested
    # on this model: reasoning_effort "none" is ignored, that kwarg works.
    #
    # Absolute store path: a launchd job gets launchd's minimal PATH, not a shell's.
    exec ${pkgs.llama-cpp}/bin/llama-server \
      --model "$MODEL_FILE" \
      --alias "${modelAlias}" \
      --host "${bindHost}" \
      --port "${toString port}" \
      --ctx-size "${toString ctxSize}" \
      --parallel 1 \
      --jinja \
      --n-gpu-layers 99 \
      --flash-attn on \
      --cache-type-k q8_0 \
      --cache-type-v q4_0
  '';
in
{
  environment.systemPackages = [ pkgs.llama-cpp ];

  # gpc/gpa/gpr, aistack and opencode read these. The ${VAR:-default} form in
  # .zshrc_envvars_insecure is a fallback for hosts without this module; this
  # value wins because /etc/zshenv is sourced first. Loopback by name, never a
  # LAN address: _validate_llamacpp rejects any other host.
  environment.variables = {
    LLAMA_CPP_HOST = lib.mkForce "http://${bindHost}:${toString port}";
    LOCAL_LLM_MODEL = modelAlias;
  };

  # Must be `postActivation` (via lib.mkAfter, which merges with the other
  # modules' text): nix-darwin only embeds a hardcoded list of activationScripts
  # names in the built `activate`, so any other key evaluates fine in `nix eval`
  # and then never runs. Activation runs as root, so the user's HOME needs
  # `sudo --set-home -u`.
  system.activationScripts.postActivation.text = lib.mkAfter ''
    sudo --set-home -u ${username} bash <<'USERSCRIPT'
    mkdir -p "$HOME/models"
    nohup ${modelDownloader} </dev/null >>"$HOME/models/download.log" 2>&1 &
    disown
    echo "[llama-model-downloader-local] Model check running in background -- tail ~/models/download.log"
    USERSCRIPT
  '';

  # A LaunchDaemon with UserName (not a user agent), so it starts at boot on the
  # headless desktop as well as at login on the laptops. KeepAlive restarts it
  # after a crash; until the model file exists the launcher exits 1 and launchd
  # retries (ThrottleInterval keeps that from spinning).
  launchd.daemons.llama-server-local = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "${serverLauncher}"
      ];
      EnvironmentVariables = {
        HOME = "/Users/${username}";
      };
      UserName = username;
      KeepAlive = true;
      RunAtLoad = true;
      ThrottleInterval = 30;
      StandardOutPath = "/tmp/llama-server-local.log";
      StandardErrorPath = "/tmp/llama-server-local.error.log";
    };
  };
}
