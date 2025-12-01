# nix-darwin Configuration & Dotfiles

This repository contains a comprehensive system configuration and dotfiles for both macOS and Linux systems. The setup supports both personal and work environments with shared base configurations.

## Platform-Specific Setup

- **[macOS Setup Guide](README_MACOS.md)** - nix-darwin installation and configuration
- **[Linux Setup Guide (Omarchy)](README_LINUX.md)** - Arch Linux with Hyprland desktop environment

## Repository Overview

This repository provides a unified configuration system for both macOS and Linux platforms, featuring consistent shell, terminal, and development tool configurations across operating systems.

## Terminal Configuration

All terminal emulators (Alacritty, Ghostty, Kitty) and Neovide are configured with consistent settings:

### Shared Settings

- **Font**: JetBrains Mono (Nerd Font) at size 14
- **Theme**: Catppuccin Mocha color scheme
- **Transparency**: 0.8 opacity with blur effects enabled
- **Cursor**: Non-blinking block cursor
- **Padding**: Zero padding for maximum screen space
- **Scrollback**: 100,000 lines of history
- **Shell**: Zsh with Starship prompt

### Terminal-Specific Features

- **Ghostty**: Custom CRT glow shader for visual effects
- **Kitty**: Advanced window management and layout system
- **Alacritty**: Lightweight with minimal dependencies
- **Neovide**: GUI Neovim with transparency and blur support

### Neovim Configuration

Located in `.config/nvim/`, the Neovim setup includes:

- LazyVim-based configuration with extensive LSP support
- Catppuccin theme integration
- Separate Neovide-specific settings in `lua/config/neovide.lua`
- Transparent background support via `transparent.nvim` plugin

## Tmux Configuration

Located at `.config/tmux/tmux.conf`, features include:

### Core Settings

- **Prefix**: `Ctrl+t` instead of default `Ctrl+b`
- **Window indexing**: Starts at 1 instead of 0
- **History**: 1,000,000 lines
- **Mode**: Vi key bindings
- **Mouse**: Enabled with scroll support

### Key Bindings

- **Splits**: `/` for horizontal, `-` for vertical
- **Reload**: `r` or `R` to reload config
- **Pane navigation**: `Ctrl+h/j/k/l` with vim-tmux-navigator integration
- **Window navigation**: `H` (previous), `L` (next)
- **Pane management**: `z` (zoom), `*` (sync panes), `S` (session chooser), `w` (close pane)
- **Resize**: `+` (up), `_` (down), `=` (even layout)
- **Plugin management**: `i` (install), `u` (update), `U` (clean)

### Plugins

- **TPM**: Plugin manager
- **vim-tmux-navigator**: Seamless Vim/Tmux navigation
- **tmux-resurrect & tmux-continuum**: Session persistence
- **tmux-yank**: Improved copy/paste
- **tmux-thumbs**: Quick text selection
- **tmux-fzf & tmux-fzf-url**: FZF integration and URL finder
- **tmux-sessionx**: Enhanced session management (bind: `o`)
- **tmux-floax**: Floating windows (bind: `p`)
- **Catppuccin**: Mocha theme with custom status line

### Status Line

- **Left**: Host, directory, session name, window indicator
- **Right**: Battery status (orange/peach), date/time (12-hour format)
- Custom icons for session, host, and time

## Shell Aliases

### SSH Targets

- `sshmacbook`, `sshg14`, `sshazeroth`, `sshtestazeroth`, `sshmini`, `sshdeck`

### Development Workflows

- `nxvim`: Open nix-darwin in tmux with nvim + aidev + git status
- `devim`: Open current directory in tmux with same layout
- `psvim`: Open pscloudops in tmux session

### Common Shortcuts

- `eza`: List all files in long format
- `ls`: Aliased to eza
- `tree`: Visual directory structure
- `spf`: Superfile with custom config

### Terraform

- `tfs`: Switch Terraform version
- `tfi`: Terraform init
- `tfa`: Terraform apply
- `tft`: Clean, init, validate, test
- `tfp`: Clean, init, validate, plan

### AWS

- `asl`: AWS SSO login to default session
- `sso`: Login to specific profile and set AWS_PROFILE
- `ssoswitch`: Switch profile without re-authentication
- `ssoexport`: Export credentials to environment

### Git/GitHub

- `gpr`: Interactive branch creation and draft PR workflow

## Shell Functions

### `asc()`

AWS credential management:

- `asc clear`: Unset all AWS environment variables
- `asc <profile>`: Export credentials for specified profile

### `aidev()`

Intelligent AI dev launcher:

1. Checks AWS Bedrock access
2. If available: Launches Claude Code
3. If unavailable: Prompts for action
   - Press Enter: Trigger AWS SSO login and retry
   - Press Esc: Launch Crush using OpenRouter
   - Press q: Exit

## Repository Structure

### Core Configuration Files

- **`flake.nix`** - Main Nix flake configuration (macOS)
- **`flake.lock`** - Locked dependency versions (macOS)
- **`nix-modules/macos/`** - macOS-specific nix-darwin configurations
- **`.gitconfig`** - Git configuration
- **`.stow-local-ignore`** - GNU Stow ignore patterns

### Application Configurations (`.config/`)

- **Terminal & Shell**
  - `alacritty/` - Alacritty terminal emulator
  - `ghostty/` - Ghostty terminal with custom CRT glow shader
  - `kitty/` - Kitty terminal emulator
  - `tmux/` - Terminal multiplexer
  - `starship.toml` - Starship prompt configuration

- **Development Tools**
  - `nvim/` - Complete Neovim configuration with LazyVim
    - Lua-based configuration with extensive plugin setup
    - LSP, completion, formatting, and Git integration
  - `gh/` - GitHub CLI configuration
  - `github-copilot/` - GitHub Copilot settings and session data

- **System & Productivity**
  - `btop/` - System monitor with Catppuccin theme
  - `atuin/` - Shell history sync configuration
  - `crush/` - Crush CLI tool configuration
  - `borders/` - Window borders configuration (macOS)
  - `raycast/` - Raycast extensions (macOS)

- **Window Managers & Desktop Environments**
  - `aerospace/` - AeroSpace window manager configuration (macOS)
  - `hypr/` - Hyprland configurations (Linux - see [README_LINUX.md](README_LINUX.md))
  - Various KDE/Plasma configuration files (Linux)

- **Specialized Tools**
  - `qmk/` - QMK keyboard firmware configurations
  - `brew/` - Homebrew package lists
  - `NuGet/` - .NET package manager configuration

### Shell Configuration

- **`.zshrc`** - Main Zsh configuration with modular sourcing
- **`.zshrc_*`** - Modular shell configurations:
  - `_aliases` - SSH targets, development workflows, common shortcuts, Terraform, AWS, and Git aliases
  - `_envvars_insecure` - Non-sensitive environment variables
  - `_functions` - AWS credential management (asc) and AI dev launcher (aidev) with Bedrock fallback
  - `_os_linux` - Linux-specific path and tool configurations
  - `_os_macos` - macOS-specific settings
  - `_shell` - General shell environment settings
  - `_ulimit` - File descriptor limits for AWS MCP servers

### Automation & Infrastructure

- **`ansible-linux/`** - Ansible playbooks for Fedora Linux setup (legacy - see [README_LINUX.md](README_LINUX.md))
  - `playbooks/` - Common, packages, and personal setup playbooks
  - `roles/` - Reusable Ansible roles
  - `inventory/` - Host inventory configuration

### Themes & Assets

- **`.wallpapers/`** - Collection of desktop wallpapers
- **`.themes/`** - Terminal and application themes
  - `MacOS Terminal/` - macOS Terminal.app themes

## Troubleshooting

### Shell and Plugin Issues

**Zinit not loading**:

```bash
# Zinit auto-installs on first zsh launch
# If it fails, manually install:
git clone https://github.com/zdharma-continuum/zinit.git ~/.local/share/zinit/zinit.git
```

**Tmux plugins not installed**:

```bash
# TPM (Tmux Plugin Manager) installs on first tmux launch
# Or manually: press Prefix + I in tmux
```

**Language servers missing for Neovim**:

```bash
# Python LSP
pip3 install python-lsp-server

# Node.js LSPs
npm install -g typescript-language-server bash-language-server yaml-language-server

# Go LSP
go install golang.org/x/tools/gopls@latest

# Rust LSP
rustup component add rust-analyzer
```

### Stow Conflicts

If stow reports conflicts:

1. Check `.stow-local-ignore` excludes
2. Manually resolve conflicting files
3. Consider backing up existing configs before stowing

### Platform-Specific Issues

For platform-specific troubleshooting:

- **macOS**: See [README_MACOS.md#troubleshooting](README_MACOS.md#troubleshooting)
- **Linux**: See [README_LINUX.md#troubleshooting](README_LINUX.md#troubleshooting)
