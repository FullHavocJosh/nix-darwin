#!/bin/bash
# Install MCP configurations for OpenCode, Crush, and ClaudeCode

set -e

MCP_CONFIG_DIR="$HOME/.config/mcp"
CONTEXT_GUARDIAN_DIR="$HOME/context-guardian-mcp-server"

echo "Installing MCP configurations..."

# Check if MCP server is built
if [ ! -f "$CONTEXT_GUARDIAN_DIR/dist/index.js" ]; then
	echo "Error: Context Guardian MCP server not built!"
	echo "Run: cd $CONTEXT_GUARDIAN_DIR && npm install && npm run build"
	exit 1
fi

# OpenCode
if command -v opencode &>/dev/null; then
	mkdir -p "$HOME/.opencode"
	cp "$MCP_CONFIG_DIR/opencode-mcp.json" "$HOME/.opencode/mcp.json"
	echo "✓ OpenCode MCP config installed"
else
	echo "⚠ OpenCode not found (install via: brew install opencode)"
fi

# Crush
if command -v crush &>/dev/null; then
	mkdir -p "$HOME/.crush"
	cp "$MCP_CONFIG_DIR/crush-mcp.json" "$HOME/.crush/mcp.json"
	echo "✓ Crush MCP config installed"
else
	echo "⚠ Crush not found (install via: brew install crush)"
fi

# ClaudeCode
if command -v claude-code &>/dev/null; then
	mkdir -p "$HOME/.claude"
	cp "$MCP_CONFIG_DIR/claude-desktop-mcp.json" "$HOME/.claude/mcp.json"
	echo "✓ ClaudeCode MCP config installed"
else
	echo "⚠ ClaudeCode not found (install via: brew install claude-code)"
fi

echo ""
echo "MCP configuration complete!"
echo ""
echo "To verify, run each tool and check if the context-guardian MCP server is loaded:"
echo "  - opencode --version"
echo "  - crush --version"
echo "  - claude-code --version"
