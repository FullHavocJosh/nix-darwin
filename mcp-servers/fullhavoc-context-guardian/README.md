# fullhavoc-context-guardian MCP Server

MCP server providing context about home infrastructure and AI contexts for coding assistants.

## Features

- **Infrastructure Context**: Provides network architecture, component details, and critical principles
- **File Access**: Read documentation from `~/aicontexts` and `~/home-infrastructure`
- **File Discovery**: List available markdown documentation recursively

## Tools

1. **get_infrastructure_context** - Get full infrastructure context
2. **get_network_architecture** - Get network architecture details (OPNsense vs K8s nginx)
3. **read_context_file** - Read specific documentation files
4. **list_context_files** - List available markdown files in a directory

## Architecture Principles

### Network Architecture

- **OPNsense Nginx**: Handles ALL SSL/TLS termination and security (HSTS, auth, rate limiting, WAF)
- **Kubernetes Nginx Ingress**: BASIC LOAD BALANCING ONLY (no SSL, no security)

### Critical Rules

- Never configure SSL/TLS in K8s nginx ingress resources
- All certificates managed in OPNsense
- Security policies centralized in OPNsense
- K8s ingress only routes traffic

## Deployment

This MCP server is automatically deployed by nix-darwin:

```bash
darwin-rebuild switch --flake ~/nix-darwin#macos_personal
```

The activation script will:

1. Sync source from `~/nix-darwin/mcp-servers/fullhavoc-context-guardian/`
2. Install npm dependencies
3. Build TypeScript to JavaScript
4. Make it available to AI coding tools

## Manual Build

```bash
cd ~/fullhavoc-context-guardian-mcp-server
npm install
npm run build
```

## Configuration

The MCP server is configured in:

- OpenCode: `~/.config/opencode/opencode.json`
- Crush: `~/.config/mcp/crush-mcp.json`
- Claude Desktop: `~/.config/mcp/claude-desktop-mcp.json`

## Context Files

- `infrastructure-context.json` - Core infrastructure context (preserved across syncs)
- `~/aicontexts/` - AI context documentation
- `~/home-infrastructure/` - Infrastructure as Code (K3s, Ansible, Terraform)
