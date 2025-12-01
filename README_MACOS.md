# macOS Setup Guide

This guide covers macOS-specific installation and configuration using nix-darwin.

## Prerequisites

```bash
# Enable Full Disk Access for Terminal
# System Preferences -> Privacy -> Full Disk Access -> Terminal

# Install essential tools
brew install git
softwareupdate --install-rosetta
```

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:FullHavocJosh/nix-darwin.git ~/nix-darwin
cd ~/nix-darwin
```

### 2. Install Nix Package Manager

```bash
sh <(curl -L https://nixos.org/nix/install)
```

### 3. Initial nix-darwin setup

```bash
nix run nix-darwin --extra-experimental-features "nix-command flakes" -- switch --flake ~/nix-darwin#macos_personal
```

### 4. Verify installation

```bash
which darwin-rebuild
```

### 5. Deploy configuration

```bash
# For personal setup
darwin-rebuild switch --flake ~/nix-darwin#macos_personal

# For work setup
darwin-rebuild switch --flake ~/nix-darwin#macos_work
```

### 6. Deploy dotfiles with Stow

```bash
stow . -t ~
```

## Package Management

This repository uses Nix + nix-darwin for declarative system configuration, with Homebrew for GUI applications.

### Managing Packages

- **Find packages**: `nix search nixpkgs <package-name>` or visit [search.nixos.org](https://search.nixos.org)
- **Add packages**: Edit `nix-modules/macos/packages.nix`
- **Update packages**:
  ```bash
  nix flake update
  darwin-rebuild switch --flake ~/nix-darwin#macos_personal
  ```

### Configuration Profiles

- **Personal**: `macos_personal` - Full personal development environment
- **Work**: `macos_work` - Work-specific configurations and restrictions

## macOS System Configuration

Located in `nix-modules/macos/config.nix`:

### Interface

- Dark mode enabled
- Scroll animations enabled
- Fast window resize (0.05s)
- Hidden menu bar

### Dock

- Auto-hide with 0.05s delay
- 32px tile size, 64px with magnification
- Genie minimize effect
- No recent apps or Dashboard
- All hot corners disabled (set to 1)

### Finder

- Show path bar, status bar, all files, and extensions
- Column view by default
- Current folder as search scope
- No extension change warnings
- Sort folders first
- Show POSIX path in title
- Desktop icons disabled

### Keyboard & Trackpad

- Function keys as standard F1-F12
- Fast key repeat (2) and initial repeat (15)
- No three-finger drag
- No swipe navigation

### Window Manager

- Auto-hide enabled
- Desktop icons hidden
- Click-to-show desktop disabled
- Stage Manager disabled
- No app window grouping

### Global Settings

- No press-and-hold for accents
- Cursor size: 1.25x
- Disabled: automatic capitalization, spelling correction, period substitution, dash substitution, quote substitution, inline prediction

## AeroSpace Window Manager

Located at `.config/aerospace/aerospace.toml`, configuration includes:

### Core Settings

- **Auto-start**: Enabled at login
- **Layout**: Tiles mode with horizontal orientation
- **Gaps**: 16px inner and outer gaps
- **Normalization**: Flatten containers and opposite orientation for nested containers
- **Key mapping**: QWERTY preset
- **Accordion padding**: 90px

### Workspace Assignments

All workspaces forced to main monitor:

- Communication, AI-LM-Studio, Terminal, Development, Nix-Darwin, Browser (main monitor)
- 1st through 5th Workspace (secondary monitor)

### Key Bindings

- **Alt+Enter**: Open Ghostty terminal
- **Alt+Shift+h/j/k/l**: Move focus between windows
- **Alt+Shift+Arrows**: Move focus with arrow keys
- **Alt+Ctrl+h/j/k/l**: Move windows between spaces
- **Alt+Shift+Tab**: Move window to next workspace
- **Alt+[1-9]**: Switch to numbered workspace
- **Alt+[A-F]**: Switch to named workspaces (A=Communication, B=AI-LM-Studio, C=Terminal, D=Development, E=Nix-Darwin, F=Browser)
- **Alt+Shift+[1-9/A-F]**: Move window to workspace
- **Alt+Tab**: Switch between workspaces
- **Alt+Shift+c**: Reload config
- **Alt+Shift+e**: Exit AeroSpace

### Service Mode

- **Enter**: `Alt+Shift+Semicolon`
- **Exit**: `Esc` or `Ctrl+c`
- Actions: Join with parent (join-with), flatten workspace, layout switching, window resizing

## Nix Configuration Structure

### Core Files

- **`flake.nix`** - Main Nix flake configuration with inputs and outputs
- **`flake.lock`** - Locked dependency versions
- **`nix-modules/macos/`** - Modular nix-darwin configurations
    - `packages.nix` - Homebrew packages, casks, and Mac App Store apps
    - `config.nix` - System configuration and settings
    - `personal.nix` - Personal environment specific settings
    - `work.nix` - Work environment specific settings

## Troubleshooting

### Homebrew paths

Ensure `/opt/homebrew/bin` is in PATH (Apple Silicon) or `/usr/local/bin` (Intel)

### AeroSpace not working

Grant Accessibility permissions in System Preferences

### nix-darwin errors

Run with verbose flag: 

```bash
darwin-rebuild switch --flake ~/nix-darwin#macos_personal --show-trace
```

### Missing Command Errors

If you encounter "command not found" errors after setup:

1. **Check if package is installed**:

   ```bash
   which <command>  # or: command -v <command>
   ```

2. **Check Nix installation**: Ensure Nix packages are in PATH:
   ```bash
   # Add to ~/.zshrc if missing
   export PATH="$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:$PATH"
   ```

3. **Verify darwin-rebuild**: Packages should be installed via `nix-modules/macos/packages.nix`

For general troubleshooting, see the main [README.md](README.md#troubleshooting).
