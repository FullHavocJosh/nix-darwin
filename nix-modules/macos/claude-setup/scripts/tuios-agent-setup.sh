set -euo pipefail
command -v tuios >/dev/null || exit 0
for h in $(tuios doctor agents --json | @jq@/bin/jq -r '.harnesses[] | select(.binary_path) | .harness'); do
  args=()
  if [ "$h" = claude-code ]; then
    args=(--mcp)
    if command -v claudetui >/dev/null; then args+=(--then "claudetui statusline --compact"); else args+=(--statusline); fi
  fi
  tuios integration install "$h" "${args[@]}" | { grep -v 'already .*current' || true; } | sed 's/^/[tuios] /'
done
