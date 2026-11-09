    (
      if command -v claudetui &>/dev/null; then
        libexec=/opt/homebrew/opt/claude-tui/libexec
        # One-time cleanup: older versions of the patch script also wrote
        # monthly_cost.py and patched files the slimmed script no longer
        # anchors on. Reinstall restores pristine sources to patch from.
        if [ -e "$libexec/claude_tui_core/monthly_cost.py" ]; then
          echo "[claude-tui] Reinstalling to drop old statusline patches..."
          brew reinstall claude-tui >/dev/null
          rm -f "$HOME/.claude/commands/usage-sync.md" \
            "$HOME"/.claude/monthly-cost-cache.json* \
            "$HOME"/.claude/monthly-tokens-cache.json*
        fi
        python3 "@claudeTuiUsagePatchScript@" "$libexec"
      fi
    ) || echo "WARNING: claude-tui statusline patch failed — continuing activation" >&2

