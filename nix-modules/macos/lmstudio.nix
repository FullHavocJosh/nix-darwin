{
  lib,
  username,
  ...
}:
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
    LOCAL_LLM_MODEL = "qwen/qwen3.5-9b";
  };

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
      ProgramArguments = [
        "/Applications/LM Studio.app/Contents/MacOS/LM Studio"
        "--run-as-service"
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
