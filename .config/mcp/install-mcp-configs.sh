#!/bin/bash
set -e

MCP_CONFIG_DIR="$HOME/.config/mcp"
CONTEXT_GUARDIAN_DIR="$HOME/fullhavoc-context-guardian-mcp-server"
SERVER_JS="$CONTEXT_GUARDIAN_DIR/dist/index.js"

echo "Installing MCP configurations..."

if [ ! -f "$SERVER_JS" ]; then
	echo "Error: Context Guardian MCP server not built!"
	echo "Run: cd $CONTEXT_GUARDIAN_DIR && npm install && npm run build"
	exit 1
fi

install_json() {
	local src="$1"
	local dest="$2"
	mkdir -p "$(dirname "$dest")"
	sed "s|__HOME__|$HOME|g" "$src" >"$dest"
}

if command -v opencode &>/dev/null; then
	install_json "$MCP_CONFIG_DIR/opencode-mcp.json" "$HOME/.opencode/mcp.json"
	echo "✓ OpenCode MCP config installed"
else
	echo "⚠ OpenCode not found"
fi

if command -v crush &>/dev/null; then
	install_json "$MCP_CONFIG_DIR/crush-mcp.json" "$HOME/.crush/mcp.json"
	echo "✓ Crush MCP config installed"
else
	echo "⚠ Crush not found"
fi

if command -v claude &>/dev/null; then
	claude mcp add context-guardian node "$SERVER_JS" 2>/dev/null && \
		echo "✓ Claude Code MCP server registered" || \
		echo "⚠ Claude Code MCP already registered or failed"
else
	echo "⚠ Claude Code not found"
fi

echo ""
echo "MCP configuration complete!"
