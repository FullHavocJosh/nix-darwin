# macOS Setup Guide

This guide covers macOS-specific installation and configuration using nix-darwin.

## Prerequisites

Enable Full Disk Access for Terminal:  
**System Preferences → Privacy → Full Disk Access → Terminal**

```bash
brew install git
softwareupdate --install-rosetta
```

## Installation

### 1. Clone Repository

```bash
git clone git@github.com:FullHavocJosh/nix-darwin.git ~/nix-darwin
cd ~/nix-darwin
```

### 2. Install Nix Package Manager

```bash
sh <(curl -L https://nixos.org/nix/install)
```

### 3. Deploy nix-darwin

```bash
nix run nix-darwin --extra-experimental-features "nix-command flakes" -- switch --flake ~/nix-darwin#macos_personal
```

### 4. Deploy Dotfiles

```bash
stow . -t ~
```

### 5. Subsequent Updates

```bash
darwin-rebuild switch --flake ~/nix-darwin#macos_personal
```

For work profile:

```bash
darwin-rebuild switch --flake ~/nix-darwin#macos_work
```

## Package Management

**Find packages**: Visit [search.nixos.org](https://search.nixos.org) or run:

```bash
nix search nixpkgs <package-name>
```

**Add packages**: Edit `nix-modules/macos/packages.nix`

**Update packages**:

```bash
nix flake update
darwin-rebuild switch --flake ~/nix-darwin#macos_personal
```

## Configuration Profiles

- **`macos_personal`** - Full personal development environment
- **`macos_work`** - Work-specific configurations and restrictions

## Shell Functions & Git Workflow

This repository includes powerful shell functions for AI-assisted development workflows.

### AI Provider Selection

**`aiselect`** - Configure which AI provider to use for shell functions:

```bash
aiselect              # Interactive menu to select provider
aiselect --show       # Display current configuration
```

Supported providers:

- **GitHub Copilot** (default) - Requires `gh auth login`
- **OpenCode Zen** - Requires `OPENCODE_API_KEY` in `~/.zshrc_envvars`
- **OpenRouter** - Requires `OPENROUTER_API_KEY` in `~/.zshrc_envvars`

### Git Workflow Commands

**`gpa`** - Git Partial Add with AI code review

Interactive staging with comprehensive checks:

1. **Secrets detection** - Scans for API keys, passwords, tokens
2. **Linting** - Auto-runs nixfmt, prettier, ruff on staged files
3. **Batched AI review** - Reviews code in ~300 line batches (handles large changesets)
4. **Interactive fixes** - Edit issues with AI assistance in tmux workspace

```bash
gpa                   # Select files, review, and get AI feedback
```

**`gpc`** - Git Push with Commit (AI-generated message)

Automatically generates conventional commit messages and pushes:

```bash
gpc                   # AI generates commit message and pushes
gpc --skip-readme     # Skip README update check
```

**`gpr_func`** - Git Pull Request with README generation

Creates draft PR with auto-generated README if missing:

```bash
gpr_func              # Interactive PR creation
```

### AI Development

**`aidev`** - Launch OpenCode with selected AI provider

```bash
aidev                 # Start OpenCode session
aidev --model <model> # Override model selection
```

### Required Packages for Shell Functions

All packages are automatically installed via nix-darwin/homebrew:

- **`jq`** - JSON parsing
- **`nixfmt`** - Nix formatter
- **`prettier`** - JS/TS/JSON/MD formatter
- **`ruff`** - Python linter
- **`opencode`** - AI code assistant
- **`gh`** - GitHub CLI
- **`tmux`** - Terminal multiplexer
- **`neovim`** - Text editor

These are already included in `nix-modules/macos/packages.nix`.

## Troubleshooting

**Homebrew paths**: Ensure `/opt/homebrew/bin` (Apple Silicon) or `/usr/local/bin` (Intel) is in PATH

**AeroSpace not working**: Grant Accessibility permissions in System Preferences

**nix-darwin errors**: Run with verbose flag:

```bash
darwin-rebuild switch --flake ~/nix-darwin#macos_personal --show-trace
```

**Missing Command Errors**: Ensure Nix packages are in PATH:

```bash
export PATH="$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:$PATH"
```
