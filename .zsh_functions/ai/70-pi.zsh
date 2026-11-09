# pi: local llama-server qwen/qwen3.5-9b drives the session and owns the tools. ~/.pi/agent/extensions/lumo-first.ts
# sends every message to Lumo first and runs qwen only when Lumo says files or shell are needed (";" at the start
# of a message skips Lumo; PI_LUMO_FIRST=0 turns it off). Strip AWS creds so Bedrock models
# are not auto-detected, strip infra secrets the model could read via env,
# skip AGENTS.md/CLAUDE.md (they reference MCP servers pi does not have),
# and skip startup network calls. Models are defined in ~/.pi/agent/models.json.
#
# -nc and --offline are chat-session flags. Placed before a subcommand (pi mcp list, pi install, pi update, pi auth ...)
# they make pi read the subcommand as a chat message and open the TUI, and --offline would stop update from using the
# network, so subcommands get the same credential scrubbing but no session flags.
function pi() {
  local -a session_flags=(-nc --offline)
  case "$1" in
    install|remove|uninstall|update|list|config|auth|mcp) session_flags=() ;;
  esac
  env -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
    -u AWS_BEARER_TOKEN_BEDROCK -u TRUENAS_API_KEY -u OPNSENSE_API_SECRET \
    command pi "${session_flags[@]}" "$@"
}

