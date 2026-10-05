{
  lib,
  pkgs,
  username,
  ...
}:
let
  lmStudioBin = "/Applications/LM Studio.app/Contents/MacOS/LM Studio";
  localModel = "qwen/qwen3.5-9b";

  # LM Studio itself (app + the daemon below) is declarative, but its model
  # store (~/.lmstudio/models) is not -- nothing else guarantees the model is on
  # this machine's disk, and _validate_llamacpp refuses a model that only exists
  # on an LM Link peer. This re-checks on every darwin-rebuild switch and pulls
  # the model if it is missing, the same self-healing pattern as the ollama
  # provisioner in desktop.nix. `lms get` downloads to the local disk even when
  # a linked device already has the model (seen on MacBookM2Pro, 2026-10-05).
  lmStudioModelProvisioner = pkgs.writeShellScript "lmstudio-model-provisioner" ''
    #!/usr/bin/env bash
    set -uo pipefail

    LMS="$HOME/.lmstudio/bin/lms"
    JQ="${pkgs.jq}/bin/jq"
    MODEL="${localModel}"
    LOG="$HOME/.lmstudio/provision.log"
    LOG_PREFIX="[lmstudio-model-provisioner]"

    mkdir -p "$HOME/.lmstudio"
    log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $*" | tee -a "$LOG"; }

    if [ ! -x "$LMS" ]; then
      log "lms not found at $LMS (LM Studio not installed or never launched), skipping"
      exit 0
    fi

    # `lms ls` wakes the LM Studio service if it is not running yet.
    READY=0
    for _ in $(seq 1 30); do
      if "$LMS" ls --json >/dev/null 2>&1; then
        READY=1
        break
      fi
      sleep 2
    done

    if [ "$READY" -ne 1 ]; then
      log "ERROR: LM Studio service not reachable after 60s, giving up"
      exit 1
    fi

    # deviceIdentifier is null for models on this machine's own disk.
    if "$LMS" ls --json 2>/dev/null \
        | "$JQ" -e --arg m "$MODEL" 'any(.[]; .modelKey == $m and .deviceIdentifier == null)' >/dev/null; then
      log "Model already on local disk: $MODEL -- skipping download"
      exit 0
    fi

    log "Model missing locally: $MODEL -- downloading..."
    if "$LMS" get "$MODEL" --mlx -y >> "$LOG" 2>&1; then
      log "Download complete: $MODEL"
    else
      log "ERROR: download failed for $MODEL -- see $LOG for details"
      exit 1
    fi
  '';
in
{
  # Points gpc/gpa/gpr's local-model calls (see _run_aider_local and
  # _validate_llamacpp in .zshrc_functions_ai) at this host's own LM Studio
  # server instead of a llama.cpp server. Every host talks to localhost, so
  # nothing here depends on another machine being reachable.
  #
  # Qwen3.5-9B was chosen over the 27B by measurement, on a ~30k-token prompt
  # (2026-10-05): M2 Pro prefill 156 tok/s vs 47 tok/s, and a 165k context cap
  # vs 42k. LM Studio sizes the context itself; `lms load -c` has no effect.
  #
  # LM Studio loads the model on the first request (JIT, ~8s cold, unloads
  # after 60 min idle), so the host only needs LM Studio's server running --
  # that is what the daemon below keeps up.
  environment.variables = {
    LLAMA_CPP_HOST = lib.mkForce "http://localhost:1234";
    LOCAL_LLM_BACKEND = "lmstudio";
    LOCAL_LLM_MODEL = localModel;
  };

  # Must be `postActivation` (via lib.mkAfter, which merges with the other
  # modules' text): nix-darwin only embeds a hardcoded list of activationScripts
  # names in the built `activate`, so any other key evaluates fine in `nix eval`
  # and then never runs. Activation runs as root, so the user's HOME needs
  # `sudo --set-home -u`. See the same notes in llamacpp-local.nix.
  system.activationScripts.postActivation.text = lib.mkAfter ''
    sudo --set-home -u ${username} bash <<'USERSCRIPT'
    mkdir -p "$HOME/.lmstudio"
    nohup ${lmStudioModelProvisioner} </dev/null >>"$HOME/.lmstudio/provision.log" 2>&1 &
    disown
    echo "[lmstudio-model-provisioner] Model check running in background -- tail ~/.lmstudio/provision.log"
    USERSCRIPT
  '';

  # Runs LM Studio headless, the same way `lms server start` does: that command
  # wakes "LM Studio --run-as-service" (observed on MacMiniM1, 2026-10-05) with
  # no window, serving :1234 and keeping the LM Link connector up. Without this
  # the server only exists while the GUI app is open, and the app is not a login
  # item. Modeled on the ollama daemon in desktop.nix (a LaunchDaemon with
  # UserName, so it starts at boot rather than at login).
  #
  # KeepAlive.SuccessfulExit=false: restart after a crash or kill, but stay down
  # after a deliberate clean quit. A second instance started while one is already
  # running (e.g. the first rebuild, before the manual one is stopped) hands off
  # to the running one and exits 0, so it does not respawn in a loop.
  launchd.daemons.lmstudio = {
    serviceConfig = {
      # The sh wrapper exits 0 when LM Studio is not installed on this host, which
      # SuccessfulExit=false below treats as "do not restart" -- so a host that
      # imports this module before the app is installed does not spin.
      ProgramArguments = [
        "/bin/sh"
        "-c"
        "[ -x ${lib.escapeShellArg lmStudioBin} ] || exit 0; exec ${lib.escapeShellArg lmStudioBin} --run-as-service"
      ];
      EnvironmentVariables = {
        HOME = "/Users/${username}";
      };
      UserName = username;
      KeepAlive = {
        SuccessfulExit = false;
      };
      RunAtLoad = true;
      StandardOutPath = "/tmp/lmstudio.log";
      StandardErrorPath = "/tmp/lmstudio.error.log";
    };
  };
}
