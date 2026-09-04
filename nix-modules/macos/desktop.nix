{ pkgs, lib, ... }:
let
  # Ollama itself (app + launchd daemon) is declarative below, but its
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

  # Desktop-only: the laptop has no reason to run a background LLM server for
  # game bots. This serves mod-ollama-chat on azerothcore (see aicontexts/azeroth).
  launchd.daemons.ollama = {
    serviceConfig = {
      ProgramArguments = [
        "/Applications/Ollama.app/Contents/Resources/ollama"
        "serve"
      ];
      EnvironmentVariables = {
        OLLAMA_HOST = "0.0.0.0:11434";
        OLLAMA_FLASH_ATTENTION = "1";
        OLLAMA_KV_CACHE_TYPE = "q8_0";
        # mod-ollama-chat on azerothcore allows OllamaChat.MaxConcurrentQueries = 32
        # concurrent requests, but llama-server defaults to serving 1 at a time —
        # everything else queues and times out. Raise parallelism to match real
        # demand from ~5k concurrent playerbots. llama3.2:1b is small (1.3GB) with a
        # 4096 context, so 4 parallel slots is a modest memory cost.
        OLLAMA_NUM_PARALLEL = "4";
        HOME = "/Users/havoc";
      };
      UserName = "havoc";
      KeepAlive = true;
      # (see launchd.user.agents.ollama-log-truncate below for log rotation)
      RunAtLoad = true;
      StandardOutPath = "/tmp/ollama.log";
      StandardErrorPath = "/tmp/ollama.error.log";
    };
  };

  # ollama.log/ollama.error.log are launchd-captured stdout/stderr with no rotation —
  # they grew to 4GB/42M lines of routine INFO/GIN chatter nothing consumes for
  # monitoring. launchd opens them O_APPEND, so an in-place truncate is safe with the
  # daemon running (no restart needed) — daily is simpler and more robust than
  # rename-based rotation (newsyslog), which would leave launchd's already-open fd
  # writing into the renamed/archived file instead of the fresh one.
  launchd.user.agents.ollama-log-truncate = {
    serviceConfig = {
      Label = "org.nixos.ollama-log-truncate";
      ProgramArguments = [
        "/bin/sh"
        "-c"
        "/usr/bin/truncate -s 0 /tmp/ollama.log /tmp/ollama.error.log"
      ];
      StartCalendarInterval = [
        {
          Hour = 4;
          Minute = 0;
        }
      ];
      RunAtLoad = false;
    };
  };
}
