{ pkgs, lib, ... }:
let
  # Ollama itself (app + launchd daemon) is declarative via personal.nix, but its
  # model store (~/.ollama/models) is not -- nothing else in this repo guarantees
  # a given model is actually present. This makes it self-healing: every
  # darwin-rebuild switch re-checks and re-pulls if the model has gone missing
  # (manual `ollama rm`, disk cleanup, etc). Currently just llama3.2:1b, used by
  # mod-ollama-chat for AzerothCore bot chat (see aicontexts/azeroth).
  ollamaModelProvisioner = pkgs.writeShellScript "ollama-model-provisioner" ''
    #!/usr/bin/env bash
    set -uo pipefail

    OLLAMA_BIN="/Applications/Ollama.app/Contents/Resources/ollama"
    MODEL="llama3.2:1b"
    LOG="$HOME/.ollama/provision.log"
    LOG_PREFIX="[ollama-model-provisioner]"

    mkdir -p "$HOME/.ollama"
    log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $*" | tee -a "$LOG"; }

    if [ ! -x "$OLLAMA_BIN" ]; then
      log "ollama binary not found at $OLLAMA_BIN, skipping"
      exit 0
    fi

    log "Waiting for ollama daemon to be reachable..."
    READY=0
    for _ in $(seq 1 30); do
      if "$OLLAMA_BIN" list >/dev/null 2>&1; then
        READY=1
        break
      fi
      sleep 2
    done

    if [ "$READY" -ne 1 ]; then
      log "ERROR: ollama daemon not reachable after 60s, giving up"
      exit 1
    fi

    if "$OLLAMA_BIN" list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$MODEL"; then
      log "Model already present: $MODEL -- skipping pull"
      exit 0
    fi

    log "Model missing: $MODEL -- pulling..."
    if "$OLLAMA_BIN" pull "$MODEL" >> "$LOG" 2>&1; then
      log "Pull complete: $MODEL"
    else
      log "ERROR: pull failed for $MODEL -- see $LOG for details"
      exit 1
    fi
  '';
in
{
  networking.hostName = "MacMiniM1";
  networking.computerName = "MacMiniM1";

  homebrew.casks = [
    "ollama-app"
  ];

  system.activationScripts.ollamaModelProvision.text = lib.mkAfter ''
    sudo -u havoc HOME=/Users/havoc bash -c '(nohup ${ollamaModelProvisioner} </dev/null >>"$HOME/.ollama/provision.log" 2>&1 &)'
    echo "[ollama-model-provisioner] Provisioning check running in background -- tail ~/.ollama/provision.log"
  '';
}
