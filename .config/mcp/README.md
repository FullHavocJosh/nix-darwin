# MCP Server Configuration for OpenCode and ClaudeCode

## Pending Doppler Secrets — MCP Servers

The following MCP servers were added to `~/.config/opencode/opencode.json` but require
secrets to be provisioned in Doppler before they will function. Each row lists the
environment variable name, the Doppler project and config it belongs in, and a description.

### `homelab-infra` project · `local` config

| Environment Variable  | MCP Server | Description                                                |
| --------------------- | ---------- | ---------------------------------------------------------- |
| `HETZNER_API_TOKEN`   | `hetzner`  | Hetzner Cloud API token — Console → Security → API Tokens  |
| `OPNSENSE_HOST`       | `opnsense` | OPNsense firewall URL, e.g. `https://192.168.1.1`          |
| `OPNSENSE_API_KEY`    | `opnsense` | OPNsense API key — System → Access → Users → API Keys      |
| `OPNSENSE_API_SECRET` | `opnsense` | OPNsense API secret (paired with `OPNSENSE_API_KEY`)       |
| `TRUENAS_URL`         | `truenas`  | TrueNAS base URL, e.g. `https://truenas.local`             |
| `TRUENAS_API_KEY`     | `truenas`  | TrueNAS API key — Credentials → API Keys                   |
| `AWX_URL`             | `awx`      | AWX/AAP/Ansible Tower base URL, e.g. `https://awx.homelab` |
| `AWX_TOKEN`           | `awx`      | AWX personal access token — User → Tokens                  |

### `ai-tools` project · `local` config

| Environment Variable | MCP Server        | Description                                                    |
| -------------------- | ----------------- | -------------------------------------------------------------- |
| `TFC_TOKEN`          | `terraform-cloud` | HCP Terraform / Terraform Cloud user or team API token         |
| `TFE_TOKEN`          | `terraform-hcp`   | Same token as `TFC_TOKEN` — used by the HashiCorp Docker image |

### Notes

- `OPNSENSE_API_KEY` and `OPNSENSE_API_SECRET` already exist in `~/.zshrc_envvars`
  (fallback file). Migrate them to Doppler project `homelab-infra:local` to complete the chain.
- `TRUENAS_API_KEY` already exists in `~/.zshrc_envvars`. Same — migrate to `homelab-infra:local`.
- `TFC_TOKEN` and `TFE_TOKEN` can be the same value if using a single HCP Terraform account.
- `OPNSENSE_VERIFY_SSL` is hardcoded to `false` in the MCP config; no secret needed.
- The `awx` server installs from GitHub on first run (`SurgeX-Labs/awx-mcp-server`). Pin to a
  specific commit in `opencode.json` once the integration is stable.

This directory contains MCP (Model Context Protocol) server configurations for AI coding assistants.

## Overview

The Context Guardian MCP Server enforces:

- **Methodology constraints** (no affirmations, no sycophancy)
- **Command safety** (allowed/forbidden command patterns)
- **System discovery** (available tools, zsh configs)

## Installation

After rebuilding nix-darwin, run:

```bash
# Build the MCP server
cd ~/context-guardian-mcp-server
npm install
npm run build

# Install configurations
./install-mcp-configs.sh
```

## Tools Using MCP

### OpenCode

- **Binary**: `opencode` (installed via Homebrew)
- **Config**: `~/.opencode/mcp.json`

### ClaudeCode

- **Binary**: `claude-code` (installed via Homebrew)
- **Config**: `~/.claude/CLAUDE.md` (for context) or Claude Desktop app settings

## Available MCP Tools

1. **check_command_safety** - Verify if a command is allowed
2. **list_allowed_commands** - Get allowed commands by category
3. **get_methodology_rules** - Retrieve methodology constraints
4. **discover_zshrc_files** - Find available zsh configuration
5. **check_tool_availability** - Check if a tool is installed

## Methodology Constraints

### No Affirmations

- Never say "Great question!" or "That's an excellent point"
- Never use "You're absolutely right" or "I completely agree"
- Skip all conversational padding and validation

### No Sycophancy

- If the user is wrong, correct them directly
- Never pretend to share the user's opinions
- Focus on facts over harmony

### Direct Communication

- Answer in 1-3 sentences unless detail is requested
- Use imperative voice
- Delete words that don't add information

## Customization

Edit the configuration files in `~/context-guardian-mcp-server/config/`:

- `policies.json` - Methodology rules and command policies
- `allowed-commands.json` - Allowed commands by category
