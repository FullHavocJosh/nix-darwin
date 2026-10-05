{ lib, ... }:
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
  # after 60 min idle), so the host only needs the app's server running.
  environment.variables = {
    LLAMA_CPP_HOST = lib.mkForce "http://localhost:1234";
    LOCAL_LLM_BACKEND = "lmstudio";
    LOCAL_LLM_MODEL = "qwen/qwen3.5-9b";
  };
}
