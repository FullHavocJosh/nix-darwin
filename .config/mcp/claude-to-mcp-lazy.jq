# Claude Code user-scope MCP servers (~/.claude.json .mcpServers) -> the "servers" map of mcp-lazy's
# ~/.mcp-lazy/servers.json, which OpenCode loads lazily through one proxy entry instead of starting every server.
#
# $home        the real home directory (replaces the __HOME__ placeholder).
# $superseded  JSON array of server names OpenCode must not get here: the ones mcp-stack-fullhavoc replaces.
#
# mcp-lazy starts each upstream server with { ...process.env, ...config.env } and does not expand ${VAR}, so
# credentials are left out of env entirely: the upstream process inherits them from the environment OpenCode was
# launched with (the opnsense, truenas and doppler exports in ~/.zshrc_personal). An env value is kept only when
# it is a non-empty literal whose key does not look like a credential.
def fix: if type == "string" then gsub("__HOME__"; $home) else . end;
def literal_env: (. // {})
  | with_entries(select((.value // "") != "" and ((.key | test("(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PASSPHRASE)$"; "i")) | not)))
  | map_values(fix);
(.mcpServers // {}) | to_entries
| map(select((.key != "mcp-lazy") and (.key as $k | ($superseded | index($k)) == null) and ((.value.command // "") != "")))
| map(.key as $k | .value as $v
    | {key: $k, value: ({command: ($v.command | fix), args: (($v.args // []) | map(fix))}
        + (($v.env | literal_env) as $e | if ($e | length) > 0 then {env: $e} else {} end))})
| from_entries
