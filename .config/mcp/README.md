# MCP Server Configuration for OpenCode, Crush, and ClaudeCode

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

### Crush

- **Binary**: `crush` (installed via Homebrew)
- **Config**: `~/.crush/mcp.json`

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
