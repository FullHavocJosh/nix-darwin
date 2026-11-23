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

  # Context window and KV cache types come from the device profile (RAM class), resolved by the launcher at start:
  # one slot (--parallel 1) gets the whole window. Same file the shell helpers source.
  profileFile = pkgs.writeText "llama-profile.sh" (builtins.readFile ../../.config/llama/profile.sh);

  # The on-demand tier-0 builder and local_edit model (.config/aistack/local_edit_mcp.py loads it on port 8082 with
  # -ngl 99 -c 32768 -np 1 -fa on --jinja, f16 KV, and unloads it after 2 idle minutes; it peaks near 6.7 GB RSS next
  # to the always-on 9B; measured 37.6 tok/s generation on the M2 Pro with reasoning effort low); downloaded only on
  # hosts with 24 GB or more; the Qwen3-Coder-30B is no longer downloaded by this module (gpt-oss replaces it in tier-0;
  # a copy already in ~/.models stays until the user deletes it).
  gptOssModel = {
    hfRepo = "ggml-org/gpt-oss-20b-GGUF";
    file = "gpt-oss-20b-MXFP4.gguf";
    sizeBytes = 12109566624;
    sha256 = "27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901";
    minRamGb = 24;
  };

  mkDownloader =
    name: model:
    pkgs.writeShellScript "llama-model-downloader-${name}" ''
      #!/usr/bin/env bash
      set -uo pipefail

      MODELS_DIR="$HOME/.models"
      LOG="$MODELS_DIR/download.log"
      LOG_PREFIX="[llama-model-downloader-${name}]"
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

      RAM_GB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))
      if [ "$RAM_GB" -lt ${toString (model.minRamGb or 0)} ]; then
        log "${model.file}: skipped, this host has $RAM_GB GB (needs ${toString (model.minRamGb or 0)} GB)"
        exit 0
      fi

      # Hashing several GB takes a few seconds; only do it when the size already matches.
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
  modelDownloader = mkDownloader "local" model;
  gptOssDownloader = mkDownloader "gptOss" gptOssModel;

  serverLauncher = pkgs.writeShellScript "llama-server-local-launcher" ''
    #!/usr/bin/env bash
    set -euo pipefail

    . ${profileFile}
    llama_profile
    echo "[llama-server-local-launcher] profile: $LLAMA_CLASS ($LLAMA_RAM_GB GB) ctx=$LLAMA_CTX_SIZE kv=$LLAMA_KV_K/$LLAMA_KV_V" >&2

    MODEL_FILE="$HOME/.models/${model.file}"
    if [ ! -f "$MODEL_FILE" ]; then
      echo "[llama-server-local-launcher] ERROR: $MODEL_FILE not found; the downloader runs on darwin-rebuild (tail ~/.models/download.log)" >&2
      exit 1
    fi

    # Loopback only, hard-coded: no flag, variable or per-host option changes it.
    # Nothing off this machine can reach the model, and this machine's tools never
    # call another machine's model (the only remote LLM is Lumo, over HTTP).
    #
    # --parallel 1: llama-server defaults to 4 slots and divides --ctx-size across
    # them; one aider/pi conversation needs the whole window in one slot.
    #
    # --ctx-size / --cache-type-k / --cache-type-v: the device profile (.config/llama/profile.sh) by RAM. q4_0
    # values were removed: prompt processing fell to ~28 tok/s at 12K depth, vs 160-205 with q8_0 or f16.
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
      --ctx-size "$LLAMA_CTX_SIZE" \
      --parallel 1 \
      --jinja \
      --n-gpu-layers 99 \
      --flash-attn on \
      --cache-type-k "$LLAMA_KV_K" \
      --cache-type-v "$LLAMA_KV_V"
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
    # gpt-oss local_edit model (absent on hosts below 24 GB; the tool reports it is unavailable)
    LOCAL_EDIT_MODEL_FILE = "/Users/${username}/.models/${gptOssModel.file}";
  };

  # Must be `postActivation` (via lib.mkAfter, which merges with the other
  # modules' text): nix-darwin only embeds a hardcoded list of activationScripts
  # names in the built `activate`, so any other key evaluates fine in `nix eval`
  # and then never runs. Activation runs as root, so the user's HOME needs
  # `sudo --set-home -u`.
  system.activationScripts.postActivation.text = lib.mkAfter ''
    sudo --set-home -u ${username} bash <<'USERSCRIPT'
    mkdir -p "$HOME/.models"
    nohup bash -c '${modelDownloader}; ${gptOssDownloader}' </dev/null >>"$HOME/.models/download.log" 2>&1 &
    disown
    echo "[llama-model-downloader-local] Model check running in background -- tail ~/.models/download.log"
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
