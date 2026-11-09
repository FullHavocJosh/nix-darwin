    # Determine which MCP servers this host should NOT run. Personal
    # machines (laptop/desktop) skip work-only servers (Jira, AWS/Terraform
    # infra tooling); the work machine skips personal homelab servers
    # (Hetzner/OPNsense/TrueNAS/AWX) plus Doppler (personal secrets flow
    # only). Same list gates both the Claude Code sync and the OpenCode
    # opencode.json patch below, so the two stay in lockstep.
    HOSTNAME_LOCAL=$(scutil --get LocalHostName 2>/dev/null)
    case "$HOSTNAME_LOCAL" in
      MacBookM2Pro*|MacMiniM1*)
        MCP_EXCLUDE_SERVERS="atlassian mcp-context-guardian-perfectserve"
        ;;
      MacBookM3Pro*)
        MCP_EXCLUDE_SERVERS="hetzner opnsense truenas awx doppler oczen"
        ;;
      *)
        MCP_EXCLUDE_SERVERS=""
        ;;
    esac

