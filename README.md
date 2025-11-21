# nix-darwin Configuration & Dotfiles

This repository contains a comprehensive system configuration for macOS using nix-darwin, along with dotfiles and configurations for various development tools and applications. The setup supports both personal and work environments with shared base configurations.

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

**Quick Start**: If you prefer automated installation, see the [Ansible (Linux)](#ansible-linux) section below. The following manual installation provides the same packages.

```bash
# Essential prerequisites
sudo dnf install -y git ansible stow

# Core packages required by .zshrc and configurations
sudo dnf install -y \
    zsh \
    fzf \
    neovim \
    tmux \
    gh \
    openssl

# Note: These tools require special installation:
# - starship: Install via script: curl -sS https://starship.rs/install.sh | sh
# - atuin: Install via script: bash <(curl --proto '=https' --tlsv1.2 -sSf https://setup.atuin.sh)
# - eza, zoxide: Install via cargo (see "Additional cargo-based tools" below)
# - awscli2: Install from AWS: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
# - terraform: Install from HashiCorp: https://developer.hashicorp.com/terraform/install

# Development tools referenced in shell configuration
sudo dnf install -y \
    golang \
    python3 \
    python3-pip \
    python3-devel \
    rust \
    cargo \
    nodejs \
    npm \
    cmake \
    make \
    gcc \
    gcc-c++

# CLI tools referenced in aliases and functions
sudo dnf install -y \
    fd-find \
    ripgrep \
    btop \
    fastfetch \
    tree \
    stow \
    watch \
    telnet \
    tar \
    gzip \
    unzip \
    which \
    htop \
    vim \
    curl \
    wget \
    jq

# Network tools
sudo dnf install -y \
    openssh-clients \
    sshpass

# Kubernetes tools (optional, used by zinit plugins)
sudo dnf install -y \
    kubectl \
    kubectx

# Additional development tools (optional)
sudo dnf install -y \
    ansible-lint \
    golangci-lint \
    lua-language-server \
    prettier \
    speedtest-cli \
    syncthing \
    tldr

# GUI applications (if using desktop environment)
sudo dnf install -y flatpak

# Terminal emulators (optional, choose one or more)
sudo dnf install -y alacritty kitty

# Nerd Fonts for proper icon display in terminals
sudo dnf install -y \
    jetbrains-mono-fonts-all \
    'mozilla-fira*' \
    fira-code-fonts

# Tools with configs in .config/ that need manual installation:
# - ghostty: Terminal emulator - https://ghostty.org
# - k9s: Kubernetes CLI - go install github.com/derailed/k9s@latest
# - superfile: File manager - go install github.com/MHNightCat/superfile@latest
# - crush: AI coding assistant - Install from source
# - opencode: AI coding assistant - Install from source
# - terraform-ls: Terraform LSP - Download from HashiCorp releases
# - tflint: Terraform linter - https://github.com/terraform-linters/tflint
# - tfswitch: Terraform version manager - https://tfswitch.warrensbox.com

# Hyprland desktop environment (optional, for Wayland)
sudo dnf install -y \
    hyprland \
    hyprlock \
    hypridle \
    hyprpaper \
    waybar

# Additional cargo-based tools (requires rust/cargo from above)
cargo install eza zoxide

# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install starship prompt
curl -sS https://starship.rs/install.sh | sh

# Install atuin shell history
bash <(curl --proto '=https' --tlsv1.2 -sSf https://setup.atuin.sh)

# Install AWS CLI v2 (download and run installer)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Optional: Install terraform (or use tfenv for version management)
# See: https://developer.hashicorp.com/terraform/install
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

## Package Management Overview

This repository uses different package management strategies depending on the platform:

- **macOS**: Nix + nix-darwin for declarative system configuration, with Homebrew for some GUI applications
- **Fedora Linux**: Manual DNF installation OR Ansible automation for repeatable setup
- **Cross-platform**: Cargo (Rust), npm (Node.js), pip (Python), and Go for language-specific tools

The README provides comprehensive Fedora package lists that match all tools referenced in:

- `.zshrc*` shell configuration files
- `.config/*` application configurations
- Aliases and functions in shell files

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

For Fedora Linux systems, use the included Ansible playbooks to automate package installation:

```bash
cd ansible-linux
# Install base packages from roles/linux-packages/tasks/main.yml
ansible-playbook -i inventory/fedora playbooks/linux-base.yml --tags packages

# Install GUI applications (if using desktop)
ansible-playbook -i inventory/fedora playbooks/linux-base.yml --tags gui

# Apply personal configuration
ansible-playbook -i inventory/fedora playbooks/linux-personal.yml
```

The Ansible playbooks in `ansible-linux/roles/linux-packages/tasks/main.yml` install:

- Development tools (Go, Python, Rust, Node.js, Neovim)
- CLI tools (fd, fzf, ripgrep, btop, tmux, zsh)
- Network tools (SSH clients)
- Language servers (Python LSP, TypeScript, Bash, YAML, Go, Rust)
- Cargo tools (eza, zoxide)

**Note**: See the "Prerequisites - For Fedora Linux" section above for the complete manual package installation list, or use the Ansible playbooks for automated setup.

## Required Packages by Configuration

This section maps each configuration directory in `.config/` to its required Fedora packages:

### Terminal Emulators

- **alacritty/** → `alacritty`
- **kitty/** → `kitty`
- **ghostty/** → Manual install from [ghostty.org](https://ghostty.org)
- **tmux/** → `tmux` (includes TPM plugin manager, auto-installed)

### Development Tools

- **nvim/** → `neovim` + language servers via npm/pip
  - Requires: `nodejs`, `npm`, `python3-pip`, `golang`, `rust`, `cargo`
  - LazyVim auto-installs plugins on first run
- **gh/** → `gh` (GitHub CLI)
- **git/** → `git` (Git configuration)
- **opencode/** → Manual install from source
- **qmk/** → QMK firmware tools (manual install)

### Shell & CLI Tools

- **starship.toml** → `starship` (prompt)
- **atuin/** → `atuin` (shell history sync)
- **superfile/** → Manual install or via go: `go install github.com/MHNightCat/superfile@latest`
- **btop/** → `btop` (system monitor)
- **crush/** → Manual install from source

### Cloud & Infrastructure

- **k9s/** → `go install github.com/derailed/k9s@latest` (Kubernetes CLI)
- AWS CLI required for shell functions → `awscli2`
- Terraform required for aliases → `terraform`

### Desktop Environment (Linux/Wayland)

- **hypr/** → `hyprland`, `hyprlock`, `hypridle`, `hyprpaper`
- **waybar/** → `waybar`
- **aerospace/** → macOS only (window manager)
- **borders/** → macOS only (JankyBorders)

### Additional Tools

- **brew/** → Homebrew package lists (macOS only)
- **AWSVPNClient/** → AWS VPN Client (manual install)

### Shell Dependencies (.zshrc)

The following packages are required by shell configurations:

- `zsh` - Shell itself
- `starship` - Prompt (.zshrc:14)
- `atuin` - History sync (.zshrc:33-35)
- `fzf` - Fuzzy finder (.zshrc:37-39)
- `zoxide` - Smart cd (.zshrc:42)
- `eza` - Modern ls (.zshrc_aliases:13-14)
- `neovim` - Editor (aliases and functions)
- `tmux` - Terminal multiplexer (nxvim, devim, psvim aliases)
- `gh` - GitHub CLI (gpr alias)
- `git` - Version control
- `aws` - AWS CLI (asl, sso, ssoswitch, ssoexport aliases)
- `terraform` - Infrastructure as code (tfs, tfi, tfa, tft, tfp aliases)
- `ssh` - Remote connections (ssh\* aliases)

### Zinit Plugin Manager

Zinit is auto-installed by `.zshrc_shell` on first run. It manages:

- Oh My Zsh plugins (git, sudo, kubectl, kubectx, rust, command-not-found)
- zsh-completions, zsh-autosuggestions, zsh-syntax-highlighting

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

## Hyprland Configuration (Nobara KDE)

Complete Wayland compositor setup optimized for Nobara KDE with **minimal package installation**. Leverages KDE's built-in tools for maximum integration. See [HYPRLAND_MIGRATION.md](.config/hypr/HYPRLAND_MIGRATION.md) for full documentation.

### Features

- **KDE Integration**: Uses Konsole, Spectacle, Dolphin, Klipper, KRunner - all pre-installed on Nobara
- **Minimal Packages**: Only 5 packages needed (hyprland, hyprlock, hypridle, hyprpaper, waybar)
- **Modular Structure**: Organized into defaults, locals, bindings, apps, and scripts
- **Catppuccin Mocha Theme**: Consistent theming across Hyprland and Waybar
- **Native Tools**: PipeWire/wpctl audio, KDE notifications via qdbus
- **Helper Scripts**: Launch terminal in CWD, toggle gaps, audio switching, power menu, screen recording
- **Smart Window Rules**: App-specific opacity, workspace assignments, and floating rules
- **Complete Bindings**: Tiling, media controls, utilities, and clipboard management

### Quick Start (Nobara KDE)

1. **Install ONLY 5 packages**:

   ```bash
   sudo dnf install hyprland hyprlock hypridle hyprpaper waybar
   ```

   That's it! Everything else uses KDE defaults already installed.

2. **Make scripts executable**:

   ```bash
   chmod +x ~/.config/hypr/scripts/*.sh
   ```

3. **Configure monitors** (edit `.config/hypr/locals/monitors.conf`)

4. **Set wallpaper** (edit `.config/hypr/hyprpaper.conf`)

5. **Launch Hyprland** from TTY

### Key Bindings

- **SUPER + SPACE**: Application launcher (KRunner)
- **SUPER + RETURN**: Terminal (Konsole)
- **SUPER + E**: File manager (Dolphin)
- **SUPER + 1-9**: Switch workspace
- **SUPER + Arrow Keys**: Move focus
- **SUPER + W**: Close window
- **SUPER + T**: Toggle floating
- **SUPER + F**: Fullscreen
- **PRINT**: Screenshot with selection (Spectacle)
- **SUPER + ESCAPE**: Power menu (KDE)
- **SUPER + CTRL + V**: Clipboard history (Klipper)

### Waybar Modules

Status bar with: Launcher, Workspaces, Window Title, Clock, System Tray, Bluetooth, Network, Audio, CPU, Memory, Temperature, Battery, Power

All styled with Catppuccin Mocha colors and interactive tooltips.

## Included Applications & Tools

### Development

- Neovim with LazyVim, Go, Python, Rust toolchains
- Language servers, formatters, and linters
- Git, GitHub CLI, and development utilities

### Terminals & Shell

- Alacritty, Ghostty, Kitty, Neovide
- Tmux, Zsh with Starship prompt
- Modern CLI tools: eza, fd, ripgrep, bat, fzf

### Productivity

- AeroSpace window manager, Raycast launcher
- System monitoring (btop), file management, and utilities

### Creative & Media

- Krita, VLC, Plexamp, and various media tools

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
    - `aerospace/` - AeroSpace window manager configuration (macOS)
    - `raycast/` - Raycast extensions (Slack integration)
    - `borders/` - Window borders configuration
    - `btop/` - System monitor with Catppuccin theme
    - `atuin/` - Shell history sync configuration
    - `crush/` - Crush CLI tool configuration

- **Desktop Environments**
    - **Hyprland (Fedora/Linux)** - Complete Wayland compositor setup
        - `hypr/` - Hyprland configuration with Catppuccin Mocha theme
            - Modular structure: defaults, locals, bindings, apps, scripts
            - Migrated from Omarchy to pure Fedora-compatible tools
            - See [HYPRLAND_MIGRATION.md](.config/hypr/HYPRLAND_MIGRATION.md) for details
        - `waybar/` - Status bar with Catppuccin theme and custom modules
    - **KDE/Plasma** - Various KDE configuration files for Linux compatibility
        - Plasma desktop, Konsole, and system settings

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

## Troubleshooting

### Missing Command Errors

If you encounter "command not found" errors after setup:

1. **Check if package is installed**:

   ```bash
   which <command>  # or: command -v <command>
   ```

2. **Common missing packages**:
   - `starship` → `sudo dnf install starship`
   - `eza` → `cargo install eza` (requires rust/cargo)
   - `zoxide` → `cargo install zoxide`
   - `atuin` → Follow [atuin.sh](https://atuin.sh) installation guide
   - `fzf` → `sudo dnf install fzf`
   - `gh` → `sudo dnf install gh`
   - `terraform` → Download from [terraform.io](https://terraform.io) or use `tfenv`
   - `kubectl` → `sudo dnf install kubectl`

3. **Zinit not loading**:

   ```bash
   # Zinit auto-installs on first zsh launch
   # If it fails, manually install:
   git clone https://github.com/zdharma-continuum/zinit.git ~/.local/share/zinit/zinit.git
   ```

4. **Tmux plugins not installed**:

   ```bash
   # TPM (Tmux Plugin Manager) installs on first tmux launch
   # Or manually: press Prefix + I in tmux
   ```

5. **Language servers missing for Neovim**:

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

6. **Path issues**:
   ```bash
   # Ensure these are in your PATH:
   export PATH="$HOME/.local/bin:$HOME/go/bin:$HOME/.cargo/bin:$PATH"
   ```

### Fedora-Specific Issues

- **Hyprland not starting**: Ensure you're on Wayland, not X11
- **Waybar not appearing**: Check `waybar --log-level debug` for errors
- **AWS CLI v2**: Use `awscli2` package on Fedora, not `aws-cli`

### macOS-Specific Issues

- **Homebrew paths**: Ensure `/opt/homebrew/bin` is in PATH (Apple Silicon) or `/usr/local/bin` (Intel)
- **AeroSpace not working**: Grant Accessibility permissions in System Preferences
- **nix-darwin errors**: Run with verbose flag: `darwin-rebuild switch --flake ~/nix-darwin#macos_personal --show-trace`
