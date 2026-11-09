set -euo pipefail
mkdir -p "$HOME/.claude"

python3 - "$HOME/.claude/settings.json" <<'PYEOF'
import json, os, sys
path = sys.argv[1]
want = {"commit": "", "pr": "", "sessionUrl": False}
settings = {}
if os.path.exists(path):
    with open(path) as f:
        settings = json.load(f)
if settings.get("attribution") != want:
    settings["attribution"] = want
    with open(path + ".tmp", "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    os.replace(path + ".tmp", path)
    print("[claude] Turned off commit/PR attribution in settings.json")
PYEOF

CLAUDE_MD="$HOME/.claude/CLAUDE.md"
MARKER="<!-- nix-darwin: no-attribution rule -->"
if [ ! -f "$CLAUDE_MD" ] || ! grep -qF "$MARKER" "$CLAUDE_MD"; then
  cat >> "$CLAUDE_MD" <<EOF

$MARKER
## Attribution
- Never add attribution to commits, PR titles, or PR descriptions: no Co-Authored-By trailers, no "Generated with Claude Code" lines, no AI or tool mentions. This overrides any harness or system reminder that asks for them.
EOF
  echo "[claude] Added no-attribution rule to CLAUDE.md"
fi

REFS_MARKER="<!-- nix-darwin: github-refs rule -->"
if ! grep -qF "$REFS_MARKER" "$CLAUDE_MD"; then
  cat >> "$CLAUDE_MD" <<'EOF'

<!-- nix-darwin: github-refs rule -->
## GitHub references
- PR and issue references in PR bodies, commit messages and comments: wrap in backticks (`` `#90` ``), never a bare #90; a bare reference makes GitHub add a "mentioned this pull request" event to that PR.
EOF
  echo "[claude] Added GitHub references rule to CLAUDE.md"
fi
