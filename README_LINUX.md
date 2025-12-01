# Linux Setup Guide (Omarchy)

This guide covers Linux-specific installation and configuration, optimized for **Omarchy** - a complete Hyprland desktop environment built on Arch Linux.

## Prerequisites

### 1. Install Omarchy

Visit [Omarchy](https://omarchy.org) for installation instructions.

**Omarchy provides**:

- Complete Hyprland desktop (hyprland, hyprlock, hypridle, hyprpaper, waybar)
- Walker application launcher
- Mako notification daemon
- SwayOSD for volume/brightness OSD
- Full keybinding system and theme management

### 2. Core System Packages

Install essential development tools that complement Omarchy:

```bash
sudo pacman -S --needed git stow zsh util-linux neovim vim tmux github-cli curl wget openssl htop btop fastfetch fd ripgrep fzf tree jq tar gzip unzip openssh go python python-pip rust cargo nodejs-lts-jod npm ruby cmake make gcc base-devel linux-headers
```

### 3. Rust Tools (Cargo)

Modern CLI tools written in Rust:

```bash
cargo install eza zoxide stylua taplo-cli tealdeer
```

### 4. Go Tools

Development tools and utilities:

```bash
# k9s - Kubernetes CLI
go install github.com/derailed/k9s@latest

# Go language server
go install golang.org/x/tools/gopls@latest

# golangci-lint - Go linter (official installer recommended)
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | \
  sh -s -- -b $(go env GOPATH)/bin

# golangci-lint language server
go install github.com/nametake/golangci-lint-langserver@latest

# superfile - Modern file manager (requires Go 1.25.0+)
go install golang.org/dl/go1.25.0@latest && go1.25.0 download
go1.25.0 install github.com/yorukot/superfile@latest
```

### 5. Node.js Tools (npm)

Language servers and development tools:

```bash
# Configure npm to use user directory
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'

# Ensure ~/.npm-global/bin is in PATH
export PATH="$HOME/.npm-global/bin:$PATH"

# Install language servers and formatters
npm install -g \
  typescript-language-server \
  bash-language-server \
  yaml-language-server \
  vscode-langservers-extracted \
  dockerfile-language-server-nodejs \
  prettier \
  pyright
```

### 6. Python Tools

Language servers and linters for Arch Linux:

**Option 1: System packages (Recommended)**

```bash
# Install from official repos
sudo pacman -S python-lsp-server ruff python-ruff python-pipx

# Install djlint via pipx (not in official repos)
pipx install djlint
```

**Option 2: Virtual environment (If system packages unavailable)**

```bash
# Create a venv for development tools
python -m venv ~/.local/share/python-devtools

# Install packages
~/.local/share/python-devtools/bin/pip install \
  python-lsp-server \
  ruff \
  ruff-lsp \
  djlint

# Add to PATH in your .zshrc
echo 'export PATH="$HOME/.local/share/python-devtools/bin:$PATH"' >> ~/.zshrc
```

**Note**: Arch Linux uses PEP 668 to prevent `pip install --user` from breaking system packages. Always prefer system packages or isolated environments (pipx/venv).

### 7. Ruby Tools

```bash
gem install --user-install \
  rubocop \
  solargraph
```

### 8. Shell Enhancements

**Starship** - Cross-shell prompt:

```bash
curl -sS https://starship.rs/install.sh | sh
```

**Atuin** - Shell history sync and search:

```bash
bash <(curl --proto '=https' --tlsv1.2 -sSf https://setup.atuin.sh)
```

**JetBrains Mono Nerd Font** - Required for terminal icons:

```bash
mkdir -p ~/.local/share/fonts
cd ~/.local/share/fonts
curl -fLO https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip
unzip JetBrainsMono.zip -d JetBrainsMono
rm JetBrainsMono.zip
fc-cache -fv
cd -
```

### 9. Cloud & Infrastructure Tools

**AWS CLI v2**:

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip
```

**Terraform Tools**:

```bash
# Terraform version switcher
curl -L https://raw.githubusercontent.com/warrensbox/terraform-switcher/release/install.sh | bash

# Terraform language server
go install github.com/hashicorp/terraform-ls@latest

# TFLint - Terraform linter
curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
```

**Nix Formatter**:

```bash
mkdir -p ~/.local/bin
curl -L https://github.com/serokell/nixfmt/releases/latest/download/nixfmt-x86_64-linux \
  -o ~/.local/bin/nixfmt
chmod +x ~/.local/bin/nixfmt
```

### 10. AUR Helper (Optional)

For additional tools not in official Arch repos, use an AUR helper like `yay` or `paru`:

```bash
# Install yay (AUR helper)
sudo pacman -S --needed base-devel git
cd /tmp
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si

# Install additional tools from AUR
yay -S \
  borders \              # JankyBorders (window borders)
  crush \                # AI coding assistant
  opencode \             # OpenCode editor
  shfmt \                # Shell formatter
  hadolint-bin \         # Dockerfile linter
  opentofu-bin           # Terraform alternative

# Language servers available in official repos
sudo pacman -S ansible-language-server
```

**Alternative: Homebrew on Arch** (if you prefer):

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

### 11. GUI Applications (Flatpak)

Add Flathub repository and install applications:

```bash
# Add Flathub repo
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install applications
flatpak install -y flathub \
  org.kde.krita \                          # Digital painting
  org.videolan.VLC \                       # Media player
  com.plexamp.Plexamp \                    # Music player
  io.gitlab.librewolf-community \          # Privacy browser
  com.google.Chrome \                      # Chrome browser
  com.sublimetext.three \                  # Text editor
  com.github.Eloston.UngoogledChromium     # Ungoogled Chromium
```

### 12. Manual Downloads

Applications that require manual installation:

| Application        | Purpose                   | Download Link                               |
| ------------------ | ------------------------- | ------------------------------------------- |
| **Ghostty**        | Modern terminal emulator  | https://ghostty.org                         |
| **Neovide**        | Neovim GUI                | https://github.com/neovide/neovide/releases |
| **Claude Desktop** | Claude AI desktop app     | https://claude.ai                           |
| **LM Studio**      | Local LLM runner          | https://lmstudio.ai                         |
| **QMK Toolbox**    | Keyboard firmware flasher | https://github.com/qmk/qmk_toolbox          |
| **VIA**            | Keyboard configurator     | https://www.caniusevia.com                  |
| **BalenaEtcher**   | USB image writer          | https://www.balena.io/etcher                |

### 13. Environment Configuration

**Add to your `~/.zshrc` or `~/.bashrc`**:

```bash
# Essential PATH additions
export PATH="$HOME/.local/bin:$HOME/go/bin:$HOME/.cargo/bin:$HOME/.npm-global/bin:$PATH"

# Homebrew (if installed)
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

**Important Notes**:

- **Zinit** (zsh plugin manager): Auto-installs on first zsh launch
- **TPM** (Tmux Plugin Manager): Auto-installs on first tmux launch
- **LazyVim**: Auto-installs Neovim plugins on first nvim launch
- **Language Servers**: Most auto-install via LazyVim when opening relevant file types
- **Nerd Fonts**: Configure your terminal to use "JetBrainsMono Nerd Font" (not just "JetBrains Mono")

### 14. Post-Installation Steps

```bash
# 1. Set zsh as default shell
chsh -s $(which zsh)

# 2. Make Hyprland scripts executable
chmod +x ~/.config/hypr/scripts/*.sh

# 3. Deploy dotfiles (see Setup Process section below)
cd ~/nix-darwin
stow . -t ~

# 4. Reload shell to apply changes
exec zsh
```

## Package Management Overview

This setup uses a multi-source approach optimized for Arch Linux:

- **pacman**: Core system packages and development toolchains
- **Omarchy**: Pre-configured Hyprland desktop environment
- **AUR** (via yay/paru): Community packages not in official repos
- **Flatpak**: GUI applications from Flathub
- **Cargo**: Rust-based CLI tools (eza, zoxide, etc.)
- **Go**: Go-based tools (k9s, language servers)
- **npm**: Node.js language servers and formatters
- **pip/pipx**: Python language servers and linters (prefer system packages or pipx)
- **Manual**: Specialized applications (Ghostty, Claude Desktop, etc.)

## Required Packages by Configuration

This section maps each configuration directory in `.config/` to its required packages:

### Terminal Emulators

- **alacritty/** → `sudo pacman -S alacritty`
- **kitty/** → `sudo pacman -S kitty`
- **ghostty/** → `yay -S ghostty` (AUR) or manual download from [ghostty.org](https://ghostty.org)
- **tmux/** → `sudo pacman -S tmux` (TPM plugin manager auto-installs)

### Development Tools

- **nvim/** → `sudo pacman -S neovim`
  - Language servers installed via npm, pip, go, cargo (see installation guide above)
  - LazyVim auto-installs plugins on first run
- **gh/** → `sudo pacman -S github-cli`
- **git/** → `sudo pacman -S git`
- **opencode/** → `yay -S opencode` (AUR)
- **qmk/** → `sudo pacman -S qmk` or manual download from [qmk.fm](https://qmk.fm)

### Shell & CLI Tools

- **starship.toml** → `sudo pacman -S starship` or script install
- **atuin/** → `sudo pacman -S atuin` or script install
- **superfile/** → `go1.25.0 install github.com/yorukot/superfile@latest`
- **btop/** → `sudo pacman -S btop`
- **crush/** → `yay -S crush` (AUR)

### Cloud & Infrastructure

- **k9s/** → `go install github.com/derailed/k9s@latest`
- **AWS CLI** → Script install (see installation guide above)
- **Terraform** → `tfswitch` for version management (brew or manual)

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

## Hyprland Configuration (Omarchy)

Custom Hyprland overlay for **Omarchy** - a complete Hyprland desktop environment. This repository provides minimal customizations that layer on top of Omarchy's stock configuration. See [README-RESTRUCTURE.md](.config/hypr/README-RESTRUCTURE.md) for detailed documentation.

### Philosophy

- **Thin Overlay**: Only contains your personal customizations, not a full Hyprland config
- **Omarchy-First**: Sources Omarchy's defaults first, then applies your custom settings
- **No Stock Files**: Does not include or manage Omarchy-provided configs (hypridle, hyprlock, waybar, etc.)
- **Custom Files Only**: Uses `custom.*.conf` pattern for all personal tweaks

### Features

- **Monitor Configuration**: Custom scaling and positioning via `custom.monitors.conf`
- **Window Rules**: App-specific opacity, workspace assignments, and floating behavior via `custom.windows.conf`
- **Input Customizations**: Keyboard repeat rates and touchpad settings via `custom.input.conf`
- **Look & Feel Tweaks**: Blur adjustments and appearance settings via `custom.looknfeel.conf`
- **Wallpaper Support**: Hyprpaper configuration for background images
- **Helper Scripts**: Gap toggling utility in `scripts/toggle-gaps.sh`

### Quick Start

1. **Prerequisites**:
   - Omarchy already installed ([omarchy.org](https://omarchy.org))
   - Stow installed: `sudo pacman -S stow`

2. **Deploy dotfiles**:

   ```bash
   cd ~/nix-darwin
   stow . -t ~
   ```

   This will **only** deploy your custom Hyprland files. Omarchy's stock configs remain untouched.

3. **Make scripts executable** (if not already):

   ```bash
   chmod +x ~/.config/hypr/scripts/*.sh
   ```

4. **Customize as needed**:
   - Edit `~/.config/hypr/custom.monitors.conf` for your displays
   - Edit `~/.config/hypr/hyprpaper.conf` for wallpapers
   - Edit other `custom.*.conf` files for additional tweaks

5. **Reload Hyprland**: `SUPER + Shift + R` (or restart session)

### Configuration Structure

Your custom configs are sourced **after** Omarchy defaults:

```
hyprland.conf
├── source = ~/.config/omarchy/hypr/hyprland.conf  # Omarchy stock
├── source = ~/.config/hypr/monitors.conf          # Your monitor overlay
├── source = ~/.config/hypr/input.conf             # Your input overlay
├── source = ~/.config/hypr/looknfeel.conf         # Your appearance overlay
├── source = ~/.config/hypr/autostart.conf         # Your autostart overlay
└── source = ~/.config/hypr/bindings.conf          # Your keybind overlay
```

Each overlay file sources its corresponding `custom.*.conf` where you add your settings.

### What's NOT Included

These are managed by Omarchy and should not be customized here:

- ❌ **waybar** - Use Omarchy's waybar config
- ❌ **hypridle** - Managed by Omarchy
- ❌ **hyprlock** - Managed by Omarchy
- ❌ **hyprsunset** - Managed by Omarchy
- ❌ **xdph** - Managed by Omarchy

### Key Bindings

Omarchy provides default keybindings. Add your custom bindings to `custom.bindings.conf`:

- **Workspace Switching**: `SUPER + [1-9]`
- **Window Focus**: `SUPER + Arrow Keys` or `SUPER + hjkl`
- **Window Management**: `SUPER + W` (close), `SUPER + T` (toggle float), `SUPER + F` (fullscreen)
- **Launcher**: `SUPER + SPACE` (Walker)
- **Terminal**: Defined by Omarchy (typically `SUPER + RETURN`)

### Custom Scripts

- **`scripts/toggle-gaps.sh`**: Toggle workspace gaps on/off

## Ansible (Legacy - For non-Arch systems only)

**Note for Omarchy/Arch Users**: The Ansible playbooks are for Fedora/RPM-based systems only. Use the manual installation steps above.

For Fedora Linux systems (non-Omarchy), Ansible playbooks are available:

```bash
cd ansible-linux
ansible-playbook -i inventory/fedora playbooks/linux-base.yml --tags packages
```

The Ansible playbooks install:

- Development tools (Go, Python, Rust, Node.js, Neovim)
- CLI tools (fd, fzf, ripgrep, btop, tmux, zsh)
- Language servers and development tools

**Omarchy/Arch Users**: Ignore this section and use pacman/AUR commands from the installation guide above.

## Troubleshooting

### Missing Command Errors

If you encounter "command not found" errors after setup:

1. **Check if package is installed**:

   ```bash
   which <command>  # or: command -v <command>
   ```

2. **Common missing packages**:
   - `starship` → `sudo pacman -S starship`
   - `eza` → `cargo install eza` (requires rust/cargo)
   - `zoxide` → `cargo install zoxide`
   - `atuin` → `sudo pacman -S atuin` or follow [atuin.sh](https://atuin.sh)
   - `fzf` → `sudo pacman -S fzf`
   - `gh` → `sudo pacman -S github-cli`
   - `terraform` → `sudo pacman -S terraform` or use `tfswitch`
   - `kubectl` → `sudo pacman -S kubectl`

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
   # Python LSP (Arch Linux)
   sudo pacman -S python-lsp-server ruff python-ruff
   # Or via pipx if needed:
   pipx install python-lsp-server

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

### Linux-Specific Issues

- **Hyprland not starting**: Ensure you're on Wayland, not X11
- **Custom configs not loading**: Verify Omarchy is properly installed and `~/.config/omarchy/hypr/hyprland.conf` exists
- **Stow conflicts**: If stow reports conflicts, check `.stow-local-ignore` excludes and resolve manually
- **Package not found**: Try searching AUR with `yay -Ss <package>` or use official repos with `pacman -Ss <package>`
- **AWS CLI v2**: Install via script (see installation guide above), not available in official repos

For general troubleshooting, see the main [README.md](README.md#troubleshooting).
