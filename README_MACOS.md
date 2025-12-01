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
