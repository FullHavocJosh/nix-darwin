# Device profile for the local llama-server: context window and KV cache types by RAM.
# Sourced by the launchd launcher (embedded by nix-modules/macos/llamacpp-local.nix) and by the shell helpers in
# .zshrc_functions_ai, so both always agree. Works in bash and zsh.
#
# KV cache: q4_0 values are slow at depth on Metal (llama-bench, Qwen3.5-9B Q4_K_M, M2 Pro 32 GB, llama.cpp 9190,
# pp4096 tokens/s at depth 0 / 12288: K q8_0 + V q4_0 118 / 28, K q8_0 + V q8_0 202 / 160, f16 + f16 212 / 205).
# At 128K context f16 costs about 2 GB more than q4_0 values, so 32 GB hosts take f16. The medium and small
# rows are sized from that data, not benchmarked on those hosts.
#
#   class   RAM       context  K     V
#   large   >= 32 GB  131072   f16   f16
#   medium  >= 16 GB   65536   q8_0  q8_0
#   small    < 16 GB   32768   q8_0  q8_0
#
# LLAMA_RAM_GB overrides the detected RAM (tests, "what would a 16 GB host get").
llama_profile() {
  LLAMA_RAM_GB="${LLAMA_RAM_GB:-$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))}"
  if [ "$LLAMA_RAM_GB" -ge 32 ]; then
    LLAMA_CLASS=large; LLAMA_CTX_SIZE=131072; LLAMA_KV_K=f16; LLAMA_KV_V=f16
  elif [ "$LLAMA_RAM_GB" -ge 16 ]; then
    LLAMA_CLASS=medium; LLAMA_CTX_SIZE=65536; LLAMA_KV_K=q8_0; LLAMA_KV_V=q8_0
  else
    LLAMA_CLASS=small; LLAMA_CTX_SIZE=32768; LLAMA_KV_K=q8_0; LLAMA_KV_V=q8_0
  fi
}
