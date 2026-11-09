set -euo pipefail
ai="$HOME/.ai"
mkdir -p "$ai/rfcs" "$ai/handoffs" "$ai/cache" "$ai/guard"
ln -sfn "$HOME/.config/ai/README.md" "$ai/README.md"
ln -sfn "$HOME/.config/ai/rfc-template.md" "$ai/rfc-template.md"
move() {
  if [ -d "$1" ] && [ ! -L "$1" ] && [ ! -e "$2" ]; then
    mv "$1" "$2" && ln -s "$2" "$1" && echo "[ai] Moved $1 to $2 (old path is now a symlink)"
  fi
}
move "$HOME/.ainfo" "$ai/ainfo"
# The tuios stack's state, from when it was the _test stack (aidev_test.py)
move "$ai/aidev_test" "$ai/aidev_tuios"
move "$ai/cache/aidev_test" "$ai/cache/aidev_tuios"
# Stow links of files the tuios stack renamed; left dangling after the rename
for old in "$HOME/.config/aistack-test" "$HOME/.zshrc_functions_test"; do
  if [ -L "$old" ] && [ ! -e "$old" ]; then
    rm "$old" && echo "[ai] Removed stale link $old"
  fi
done
move "$HOME/.aistack" "$ai/aidev"
move "$HOME/.cache/aistack-pi-ai" "$ai/ai"
move "$HOME/.cache/nix-darwin-ai/aistack-pi" "$ai/cache/aistack-pi"
move "$HOME/.cache/aistack-pi-coder" "$ai/cache/aistack-pi-coder"
move "$HOME/.cache/local-edit" "$ai/cache/local-edit"
move "$HOME/.cache/aidev-aider" "$ai/cache/aidev-aider"
move "$HOME/.cache/advisor" "$ai/guard/advisor"
move "$HOME/.cache/edit-router" "$ai/guard/edit-router"
python3 - "$HOME/.claude/settings.json" "$HOME/.claude/CLAUDE.md" <<'PYEOF'
import json, os, re, sys
path, md = sys.argv[1], sys.argv[2]
if os.path.exists(path):
    with open(path) as f:
        settings = json.load(f)
    before = json.dumps(settings, sort_keys=True)
    perms = settings.setdefault("permissions", {})
    # An Edit rule covers Write too; additionalDirectories lets Claude read ~/.ai from any project
    for key, rule in (("additionalDirectories", "~/.ai"), ("allow", "Edit(~/.ai/**)"), ("deny", "Edit(~/.ai/guard/**)")):
        rules = perms.setdefault(key, [])
        if rule not in rules:
            rules.append(rule)
    if json.dumps(settings, sort_keys=True) != before:
        with open(path + ".tmp", "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        os.replace(path + ".tmp", path)
        print("[claude] Updated settings.json: ~/.ai writable, ~/.ai/guard denied")
begin, end = "<!-- nix-darwin: shared ai dir (begin) -->", "<!-- nix-darwin: shared ai dir (end) -->"
block = begin + """
## Shared AI directory (~/.ai)
- RFCs: when the user asks for an RFC, a plan or notes to pick up later or in another tool, write
  `~/.ai/rfcs/YYYY-MM-DD-slug.md` in the format of `~/.ai/rfc-template.md` (layout: `~/.ai/README.md`). Never put
  one in a repository unless asked.
- Any model may write anywhere in `~/.ai` except `~/.ai/guard/` (hook state), advisor mode included.
- Pointed at an RFC: read it first, check its claims against the code, and move its `status:` (`ready`,
  `in-progress`, `done`) as the work moves. `aidev --rfc <name>` plans from one.
""".replace("\n    ", "\n").rstrip() + "\n" + end
text = open(md).read() if os.path.exists(md) else ""
if begin in text and end in text:
    new = re.sub(re.escape(begin) + ".*?" + re.escape(end), lambda m: block, text, flags=re.S)
else:
    new = text.rstrip("\n") + ("\n\n" if text.strip() else "") + block + "\n"
if new != text:
    with open(md + ".tmp", "w") as f:
        f.write(new)
    os.replace(md + ".tmp", md)
    print("[claude] Updated the ~/.ai rules in CLAUDE.md")
PYEOF
