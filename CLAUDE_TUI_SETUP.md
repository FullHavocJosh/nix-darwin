# Claude-TUI Integration Summary

## What Was Done

### 1. Removed claudecode.nvim

- Deleted plugin from `~/.local/share/nvim/lazy/claudecode.nvim/`
- Removed config file `~/.config/nvim/lua/plugins/claudecode.lua`
- Updated `lazy-lock.json` (backup at `lazy-lock.json.backup`)

### 2. Fixed Python PATH Issue

**File:** `~/.zshrc_os_macos`

Changed ansible-venv from auto-activation to manual activation:

```bash
# Now use this function when you need Ansible:
ansible-venv-activate
```

This prevents Python 3.9 (in ansible-venv) from overriding system Python 3.14.5 (needed for claude-tui).

### 3. Added Automatic Claude-TUI Setup

**File:** `nix-modules/macos/packages.nix`

Added two components:

#### a) `claudeTuiSetup` Helper Script

- Checks if claude-tui is already configured (idempotent)
- Configures `~/.claude/settings.json` with statusline and hooks
- Symlinks slash commands to `~/.claude/commands/tui`
- Creates marker file `~/.claude/.claudetui-configured`

#### b) Activation Hook

Added to `system.activationScripts.postUserActivation`:

```nix
# Configure claude-tui for Claude Code
(
  ${claudeTuiSetup}
) || echo "WARNING: claude-tui setup failed — continuing activation" >&2
```

## How It Works

When you run `darwin-rebuild switch`:

1. ✅ Homebrew installs/updates `claude-tui` (if needed)
2. ✅ Setup script checks for marker file `~/.claude/.claudetui-configured`
3. ✅ If not configured OR invalid:
   - Configures `settings.json` (statusline + hooks)
   - Creates command symlinks
   - Creates marker file
4. ✅ If already configured and valid: Skips setup

## Claude-TUI Features

### Statusline (Automatic)

Shows in Claude Code sessions:

- Context usage and limits
- Cost tracking
- Usage bars (session/weekly)
- Sparkline visualization
- Live tool trace

### Hooks (Automatic)

- **SessionStart** → File hotspots analysis
- **PreToolUse** → Churn warnings before edits
- **PostToolUse** → Dependency checks after edits

### Slash Commands

Use in Claude Code:

- `/tui:session` - Full session report
- `/tui:cost` - Cost analysis
- `/tui:perf` - Performance metrics
- `/tui:context` - Context report

### CLI Tools

Run in terminal:

```bash
claudetui monitor      # Live dashboard in separate terminal
claudetui chart        # Context efficiency visualization
claudetui stats        # Post-session analytics
claudetui sessions list # Browse/compare/export sessions
claudetui mode compact # Switch to 1-line statusline
claudetui mode full    # Switch to 3-line statusline (default)
```

## Files Created/Modified

### Nix-Darwin Config

- ✏️ `nix-modules/macos/packages.nix` - Added setup automation
- ✏️ `.zshrc_os_macos` - Fixed Python PATH

### Claude Code Config (Auto-created by setup)

- 📝 `~/.claude/settings.json` - Statusline and hooks config
- 🔗 `~/.claude/commands/tui` - Symlink to commands
- 📄 `~/.claude/.claudetui-configured` - Marker file

## Next Steps

1. **Commit your changes:**

   ```bash
   cd ~/nix-darwin
   git add nix-modules/macos/packages.nix .zshrc_os_macos CLAUDE_TUI_SETUP.md
   git commit -m "Add claude-tui auto-setup; remove claudecode.nvim; fix Python PATH"
   ```

2. **Apply configuration:**

   ```bash
   darwin-rebuild switch --flake ~/nix-darwin#macos_laptop
   ```

3. **Verify setup:**

   ```bash
   ls -la ~/.claude/
   cat ~/.claude/settings.json | jq .statusLine
   ls -la ~/.claude/commands/
   ```

4. **Test it:**
   ```bash
   # Open new terminal (to get updated PATH)
   claude
   # Should see statusline at the top!
   ```

## Manual Operations

### Force Reconfiguration

```bash
rm ~/.claude/.claudetui-configured
darwin-rebuild switch --flake ~/nix-darwin#macos_laptop
```

### Switch Statusline Modes

```bash
claudetui mode compact  # 1-line
claudetui mode full     # 3-line (default)
claudetui mode custom   # Interactive configurator
```

### Activate Ansible Environment

```bash
# Only when you need Ansible:
ansible-venv-activate
```

## Troubleshooting

### Python version issues

```bash
# Check current Python:
which python3
python3 --version  # Should be 3.14.5, not 3.9.6

# If still showing 3.9.6, open a new terminal
# Or manually adjust PATH:
export PATH="/opt/homebrew/bin:$PATH"
```

### Claude-TUI not configured after rebuild

```bash
# Check if setup ran:
grep claude-tui ~/Library/Logs/nix-darwin/activation*.log 2>/dev/null | tail -20

# Manually run setup:
export PATH="/opt/homebrew/bin:$PATH"
claudetui setup
```

### Settings.json not created

```bash
# Ensure directory exists:
mkdir -p ~/.claude

# Re-run darwin-rebuild:
darwin-rebuild switch --flake ~/nix-darwin#macos_laptop
```

## Reference Links

- **Claude-TUI GitHub**: https://github.com/slima4/claude-tui
- **Documentation**: https://slima4.github.io/claude-tui/
- **Homebrew Formula**: `slima4/claude-tui/claude-tui`
