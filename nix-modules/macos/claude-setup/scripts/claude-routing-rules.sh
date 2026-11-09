set -euo pipefail
mkdir -p "$HOME/.claude" "$HOME/.local/bin"
# aidev is a zsh function (.zsh_functions/tuios/); OpenCode, pi and scripts get it through this executable
ln -sfn "$HOME/.config/aistack/aidev-cli" "$HOME/.local/bin/aidev"
python3 - "$HOME/.claude/CLAUDE.md" <<'PYEOF'
import os, re, sys
path = sys.argv[1]
begin, end = "<!-- nix-darwin: model routing (begin) -->", "<!-- nix-darwin: model routing (end) -->"
block = begin + """
## Model routing
Spend Claude tokens only on what needs Claude; free and local models take the rest:
- Commits and PRs: gpr / gpa (the local 9B reviews; write the message yourself with -m/-d).
- Public web research: lumo_search (WebSearch is off). WebFetch only for an exact URL you already have.
- Edits touching 3+ files or needing 5+ edits that you can state precisely: local_edit (free on-device coder
  model), one call per file with start_line/end_line where you can and a test_cmd, then review its diff;
  oczen_edit (OpenCode Zen, free, cloud, same request) when local_edit is unavailable or failed. Measured: 3
  turns/$0.09 vs 18 turns/$0.16 by hand. Pure pattern replacements: one sed or python command; if that is not
  possible or not allowed, local_edit, not Edit by hand. A single small or subtle edit: make it yourself.
  Enforced: a hook refuses the third file edited by hand in one request.
- aidev (tuios: Claude runs free builders, the on-device 30B, then a free Zen model). A feature planned in this
  session: /aidev-handoff (you write the plan, `aidev --handoff <dir>` opens the run). One self-contained edit
  across files that a check can verify: `AIDEV_TEST_CMD="<check>" aidev -p "<exact change. Change nothing else.>"
  <files>` (blocks; in tuios the builder works in a pane), then review its diff. Plain `aidev` is the user's
  interactive planner; never run it yourself.
- Private sources (GitHub, Terraform, Atlassian and other MCP servers) and judgment calls: yourself.
""".replace("\n    ", "\n").rstrip() + "\n" + end
text = open(path).read() if os.path.exists(path) else ""
if begin in text and end in text:
    new = re.sub(re.escape(begin) + ".*?" + re.escape(end), lambda m: block, text, flags=re.S)
else:
    new = text.rstrip("\n") + ("\n\n" if text.strip() else "") + block + "\n"
if new != text:
    with open(path + ".tmp", "w") as f:
        f.write(new)
    os.replace(path + ".tmp", path)
    print("[claude] Updated the model-routing rules in CLAUDE.md")
PYEOF
