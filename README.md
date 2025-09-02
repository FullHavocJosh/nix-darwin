# nix-darwin Configuration & Dotfiles

This repository contains a comprehensive system configuration for macOS using nix-darwin, along with dotfiles and configurations for various development tools and applications. The setup supports both personal and work environments with shared base configurations.

## Repository Structure

### Core Nix Configuration
- **`flake.nix`** - Main Nix flake configuration with inputs and outputs
- **`flake.lock`** - Locked dependency versions
- **`nix-modules/macos/`** - Modular nix-darwin configurations
  - `packages.nix` - Homebrew packages, casks, and Mac App Store apps
  - `config.nix` - System configuration and settings
  - `personal.nix` - Personal environment specific settings
  - `work.nix` - Work environment specific settings

### Application Configurations (`.config/`)
- **Terminal & Shell**
  - `alacritty/` - Alacritty terminal emulator config with Catppuccin theme
  - `ghostty/` - Ghostty terminal config with CRT glow shader
  - `kitty/` - Kitty terminal emulator configuration
  - `tmux/` - Terminal multiplexer configuration
  - `ohmyposh/` - Oh My Posh prompt theme (zen.toml)

- **Development Tools**
  - `nvim/` - Complete Neovim configuration with LazyVim
    - Lua-based configuration with extensive plugin setup
    - LSP, completion, formatting, and Git integration
  - `gh/` - GitHub CLI configuration
  - `github-copilot/` - GitHub Copilot settings and session data

- **System & Productivity**
  - `aerospace/` - AeroSpace window manager configuration
  - `raycast/` - Raycast extensions (Slack integration)
  - `borders/` - Window borders configuration
  - `btop/` - System monitor with Catppuccin theme
  - `atuin/` - Shell history sync configuration
  - `crush/` - Crush CLI tool configuration

- **Desktop Environment (KDE/Plasma)**
  - Various KDE configuration files for Linux compatibility
  - Plasma desktop, Konsole, and system settings

- **Specialized Tools**
  - `qmk/` - QMK keyboard firmware configurations
  - `brew/` - Homebrew package lists
  - `NuGet/` - .NET package manager configuration

### Shell Configuration
- **`.zshrc`** - Main Zsh configuration
- **`.zshrc_*`** - Modular shell configurations:
  - `_aliases` - Command aliases
  - `_envvars_insecure` - Environment variables (non-sensitive)
  - `_functions` - Custom shell functions
  - `_os_linux` - Linux-specific configurations
  - `_os_macos` - macOS-specific configurations
  - `_shell` - General shell settings
  - `_tools` - Tool-specific configurations

### Automation & Infrastructure
- **`ansible-fedora/`** - Ansible playbooks for Fedora Linux setup
  - `playbooks/` - Common, packages, and personal setup playbooks
  - `roles/` - Reusable Ansible roles
  - `inventory/` - Host inventory configuration

### Themes & Assets
- **`.wallpapers/`** - Collection of desktop wallpapers
- **`.themes/`** - Terminal and application themes
  - `MacOS Terminal/` - macOS Terminal.app themes

### Development Environment
- **`.claude/`** - Claude AI assistant configuration and project data
- **`.gitconfig`** - Git configuration
- **`.stow-local-ignore`** - GNU Stow ignore patterns

## Installation

### Prerequisites

#### For macOS
```bash
# Enable Full Disk Access for Terminal
# System Preferences -> Privacy -> Full Disk Access -> Terminal

# Install essential tools
brew install git
softwareupdate --install-rosetta
```

#### For Fedora Linux
```bash
yum install git
```

### Setup Process

1. **Clone the repository**
   ```bash
   git clone git@github.com:FullHavocJosh/nix-darwin.git ~/nix-darwin
   cd ~/nix-darwin
   ```

2. **Install Nix Package Manager**
   ```bash
   sh <(curl -L https://nixos.org/nix/install)
   ```

3. **Initial nix-darwin setup**
   ```bash
   nix run nix-darwin --extra-experimental-features "nix-command flakes" -- switch --flake ~/nix-darwin#macos_personal
   ```

4. **Verify installation**
   ```bash
   which darwin-rebuild
   ```

5. **Deploy configuration**
   ```bash
   # For personal setup
   darwin-rebuild switch --flake ~/nix-darwin#macos_personal
   
   # For work setup
   darwin-rebuild switch --flake ~/nix-darwin#macos_work
   ```

6. **Deploy dotfiles with Stow**
   ```bash
   stow . -t ~
   ```

## Usage

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

### Ansible (Linux)
For Fedora Linux systems, use the included Ansible playbooks:
```bash
cd ansible-fedora
ansible-playbook -i inventory/local playbooks/common.yml
ansible-playbook -i inventory/local playbooks/packages.yml
ansible-playbook -i inventory/local playbooks/personal.yml
```

## Key Features

- **Declarative System Management** - Entire system configuration in code
- **Cross-Platform Support** - Configurations for both macOS and Linux
- **Modular Design** - Separate personal and work environments
- **Comprehensive Tooling** - Development tools, terminals, editors, and productivity apps
- **Theme Consistency** - Catppuccin theme across multiple applications
- **Automated Deployment** - Single command system setup and updates
- **Dotfile Management** - GNU Stow for symlink management
- **Shell Enhancement** - Modular Zsh configuration with modern tools

## Included Applications & Tools

### Development
- Neovim with LazyVim, Go, Python, Rust toolchains
- Language servers, formatters, and linters
- Git, GitHub CLI, and development utilities

### Terminals & Shell
- Alacritty, Ghostty, Kitty terminal emulators
- Tmux, Zsh with Oh My Posh, modern CLI tools (eza, fd, ripgrep, etc.)

### Productivity
- AeroSpace window manager, Raycast launcher
- System monitoring (btop), file management, and utilities

### Creative & Media
- Krita, VLC, Plexamp, and various media tools

This configuration provides a complete, reproducible development environment that can be deployed consistently across multiple machines.