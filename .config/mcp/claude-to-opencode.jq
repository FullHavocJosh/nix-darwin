# Claude Code user-scope MCP servers (~/.claude.json .mcpServers) -> OpenCode "mcp" entries.
# Secrets are never copied: a value that is empty, or whose key looks like a credential, becomes {env:KEY}
# (OpenCode resolves it from the process environment at launch, like the existing opnsense/truenas/doppler
# exports in ~/.zshrc_personal); ${VAR} placeholders become {env:VAR}; __HOME__ becomes the real home.
def fix: if type == "string"
  then gsub("__HOME__"; $home) | gsub("\\$\\{(?<v>[A-Za-z0-9_]+)\\}"; "{env:\(.v)}")
  else . end;
def envmap: with_entries(
  .key as $n
  | .value = (if (.value == null or .value == "" or ($n | test("(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PASSPHRASE)$"; "i")))
              then "{env:\($n)}" else (.value | fix) end));
(.mcpServers // {}) | to_entries | map(
  .key as $k | .value as $v
  | if ($v.url // "") != "" and ($v.command // "") == "" then
      {key: $k, value: ({type: "remote", url: ($v.url | fix), enabled: true}
        + (if ($v.headers // {} | length) > 0 then {headers: ($v.headers | with_entries(.value |= fix))} else {} end))}
    else
      {key: $k, value: ({type: "local", command: ([$v.command] + ($v.args // []) | map(fix)), enabled: true}
        + (if ($v.env // {} | length) > 0 then {environment: ($v.env | envmap)} else {} end))}
    end) | from_entries
