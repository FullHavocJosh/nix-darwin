#!/bin/bash
set -e

MCP_CONFIG_DIR="$HOME/.config/mcp"
STACK_DIR="$HOME/mcp-stack-fullhavoc"

echo "Installing MCP configurations..."

if [ ! -f "$STACK_DIR/pyproject.toml" ]; then
	echo "Error: mcp-stack-fullhavoc not found at $STACK_DIR"
	echo "Run: git clone git@github.com:FullHavocJosh/mcp-stack-fullhavoc.git $STACK_DIR && cd $STACK_DIR && uv sync"
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

if command -v claude &>/dev/null; then
	claude mcp add --scope user mcp-stack-fullhavoc -- uv run --project "$STACK_DIR" mcp-stack-fullhavoc 2>/dev/null &&
		echo "✓ Claude Code MCP server registered" ||
		echo "⚠ Claude Code MCP already registered or failed"
else
	echo "⚠ Claude Code not found"
fi

echo ""
echo "MCP configuration complete!"
