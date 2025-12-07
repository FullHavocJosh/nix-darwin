# Linux Setup Guide (Omarchy)

This guide covers Linux-specific installation and configuration, optimized for **Omarchy** - a complete Hyprland desktop environment built on Arch Linux.

## Prerequisites

### 1. Install Omarchy

Visit [Omarchy](https://omarchy.org) for installation instructions.

**Omarchy provides**: Complete Hyprland desktop, Walker launcher, Mako notifications, SwayOSD, full keybinding system and theme management.

## Installation

### 2. Core System Packages

```bash
sudo pacman -S --needed git stow zsh util-linux neovim vim tmux github-cli curl wget openssl htop btop fastfetch fd ripgrep fzf tree jq tar gzip unzip openssh go python python-pip rust cargo nodejs-lts-jod npm ruby cmake make gcc base-devel linux-headers
```

### 3. Rust Tools (Cargo)

```bash
cargo install eza zoxide stylua taplo-cli tealdeer
```

### 4. Go Tools

```bash
go install github.com/derailed/k9s@latest
go install golang.org/x/tools/gopls@latest
go install github.com/nametake/golangci-lint-langserver@latest
go install golang.org/dl/go1.25.0@latest
go1.25.0 download
go1.25.0 install github.com/yorukot/superfile@latest
```

```bash
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin
```

### 5. Node.js Tools (npm)

```bash
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH="$HOME/.npm-global/bin:$PATH"
```

```bash
npm install -g typescript-language-server bash-language-server yaml-language-server vscode-langservers-extracted dockerfile-language-server-nodejs prettier pyright
```

### 6. Python Tools

```bash
sudo pacman -S python-lsp-server ruff python-ruff python-pipx
pipx install djlint
```

### 7. Ruby Tools

```bash
gem install --user-install rubocop solargraph
```

### 8. Shell Enhancements

```bash
curl -sS https://starship.rs/install.sh | sh
```

```bash
bash <(curl --proto '=https' --tlsv1.2 -sSf https://setup.atuin.sh)
```

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

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip
```

```bash
curl -L https://raw.githubusercontent.com/warrensbox/terraform-switcher/release/install.sh | bash
go install github.com/hashicorp/terraform-ls@latest
curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
```

**Install via AUR (recommended):**

```bash
yay -S nixfmt
```

**Or manually download:**

```bash
mkdir -p ~/.local/bin
curl -L https://github.com/serokell/nixfmt/releases/latest/download/nixfmt-x86_64-linux -o ~/.local/bin/nixfmt
chmod +x ~/.local/bin/nixfmt
```

### 10. AUR Helper (Optional)

```bash
sudo pacman -S --needed base-devel git
cd /tmp
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
```

```bash
yay -S borders crush opencode shfmt hadolint-bin opentofu-bin
sudo pacman -S ansible-language-server
```

### 11. GUI Applications (Flatpak)

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

```bash
flatpak install -y flathub org.kde.krita org.videolan.VLC com.plexamp.Plexamp io.gitlab.librewolf-community com.google.Chrome com.sublimetext.three com.github.Eloston.UngoogledChromium
```

### 12. Manual Downloads

| Application      | Purpose                   | Download Link                               |
| ---------------- | ------------------------- | ------------------------------------------- |
| **Ghostty**      | Modern terminal emulator  | https://ghostty.org                         |
| **Neovide**      | Neovim GUI                | https://github.com/neovide/neovide/releases |
| **LM Studio**    | Local LLM runner          | https://lmstudio.ai                         |
| **QMK Toolbox**  | Keyboard firmware flasher | https://github.com/qmk/qmk_toolbox          |
| **VIA**          | Keyboard configurator     | https://www.caniusevia.com                  |
| **BalenaEtcher** | USB image writer          | https://www.balena.io/etcher                |

### 13. Clone and Deploy

```bash
git clone git@github.com:FullHavocJosh/nix-darwin.git ~/nix-darwin
cd ~/nix-darwin
stow . -t ~
```

### 14. Post-Installation

```bash
chsh -s $(which zsh)
chmod +x ~/.config/hypr/scripts/*.sh
exec zsh
```

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

These are already included in the installation steps above:

- **`jq`** - JSON parsing (pacman)
- **`nixfmt`** - Nix formatter (AUR: `yay -S nixfmt`)
- **`prettier`** - JS/TS/JSON/MD formatter (npm global)
- **`ruff`** - Python linter (pacman)
- **`opencode`** - AI code assistant (AUR: `yay -S opencode`)
- **`gh`** - GitHub CLI (pacman)
- **`tmux`** - Terminal multiplexer (pacman)
- **`nvim`** - Text editor (pacman)

## Notes

**Zinit** (zsh plugin manager): Auto-installs on first zsh launch  
**TPM** (Tmux Plugin Manager): Auto-installs on first tmux launch  
**LazyVim**: Auto-installs Neovim plugins on first nvim launch  
**Language Servers**: Most auto-install via LazyVim when opening relevant file types  
**Nerd Fonts**: Configure your terminal to use "JetBrainsMono Nerd Font"

## Hyprland Configuration

Custom Hyprland overlay for **Omarchy**. This repository provides minimal customizations that layer on top of Omarchy's stock configuration.

**Philosophy**: Thin overlay containing only personal customizations, not a full Hyprland config.

**Features**:

- Monitor configuration via `custom.monitors.conf`
- Window rules via `custom.windows.conf`
- Input customizations via `custom.input.conf`
- Look & feel tweaks via `custom.looknfeel.conf`
- Wallpaper support via `hyprpaper.conf`

**Reload Hyprland**: `SUPER + Shift + R`

## Troubleshooting

**Missing Command Errors**: Run `which <command>` to check if installed. Add to PATH if needed:

```bash
export PATH="$HOME/.local/bin:$HOME/go/bin:$HOME/.cargo/bin:$HOME/.npm-global/bin:$PATH"
```

**Zinit not loading**:

```bash
git clone https://github.com/zdharma-continuum/zinit.git ~/.local/share/zinit/zinit.git
```

**Tmux plugins not installed**: Press `Prefix + I` in tmux

**Language servers missing**: Most auto-install via LazyVim. Manual installation commands in sections 5-6 above.

**Hyprland not starting**: Ensure you're on Wayland, not X11

**Stow conflicts**: Check `.stow-local-ignore` excludes and resolve manually
