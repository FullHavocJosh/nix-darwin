I'll review the staged changes against the current README.md to determine if updates are needed.
Perfect! I can see that the current README.md is actually just a placeholder with meta-commentary about what should be documented. However, looking at the staged changes, I notice that **README_LINUX.md** and **README_MACOS.md** have been updated with comprehensive documentation about the new shell functions and AI workflow.

Since the main **README.md** is just a placeholder, and the platform-specific READMEs have already been updated with the new content, the main README should be updated to properly introduce the repository and point users to the appropriate platform-specific documentation.

Here's the updated README.md:

```markdown
# Nix Darwin & Linux Dotfiles

Cross-platform development environment configuration using Nix (macOS) and manual setup (Linux). Features AI-assisted development workflows, custom shell functions, and comprehensive terminal tooling.

## Platform-Specific Documentation

- **[macOS Setup Guide](README_MACOS.md)** - Nix-Darwin flake-based configuration
- **[Linux Setup Guide](README_LINUX.md)** - Arch Linux manual installation
- **[Omarchy Linux](README_OMARCHY.md)** - Arch-based distribution configuration

## Key Features

### AI-Assisted Development
- **Multi-provider support** - GitHub Copilot, OpenCode Zen, OpenRouter
- **`aiselect`** - Interactive AI provider configuration
- **`aidev`** - Launch OpenCode with selected provider
- **`gpa`** - Git staging with AI code review, linting, and secrets detection
- **`gpc`** - AI-generated commit messages with conventional commits
- **`gpr_func`** - PR creation with auto-generated documentation

### Shell Enhancements
- **Zinit** - Fast zsh plugin manager with lazy loading
- **Starship** - Cross-shell prompt with git integration
- **Atuin** - Shell history sync and search
- **Zoxide** - Smart directory navigation

### Development Tools
- **Neovim (LazyVim)** - Modern IDE configuration
- **Tmux** - Terminal multiplexer with custom keybindings
- **Ghostty/Alacritty/Kitty** - GPU-accelerated terminal emulators
- **btop/bottom** - System monitoring

## Quick Start

### macOS (Recommended)
```bash
# Clone repository
git clone https://github.com/yourusername/nix-darwin.git ~/nix-darwin
cd ~/nix-darwin

# Install Nix with flakes
sh <(curl -L https://nixos.org/nix/install)
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf

# Build configuration
nix run nix-darwin -- switch --flake ~/nix-darwin#macos_personal

# Reload shell
exec zsh
```

See [README_MACOS.md](README_MACOS.md) for detailed instructions.

### Linux (Arch-based)
```bash
# Clone repository
git clone https://github.com/yourusername/nix-darwin.git ~/nix-darwin
cd ~/nix-darwin

# Install base packages
sudo pacman -S git stow zsh curl wget neovim tmux

# Link dotfiles
stow -v --target=$HOME .

# Install additional tools
yay -S zinit-git starship atuin zoxide opencode nixfmt
```

See [README_LINUX.md](README_LINUX.md) for complete installation steps.

## Configuration Files

```
.
├── .config/              # Application configurations
│   ├── nvim/            # LazyVim configuration
│   ├── tmux/            # Tmux configuration
│   ├── ghostty/         # Ghostty terminal
│   ├── alacritty/       # Alacritty terminal
│   └── hypr/            # Hyprland (Linux only)
├── nix-modules/         # Nix-Darwin configurations
│   └── macos/           # macOS-specific modules
├── scripts/             # Utility scripts
├── .zshrc*              # Zsh configuration files
└── README*.md           # Documentation
```

## AI Provider Setup

The repository includes a flexible AI provider system for development workflows.

### Configure Provider
```bash
aiselect              # Interactive menu
aiselect --show       # Show current configuration
```

### Authentication
```bash
# GitHub Copilot (default)
gh auth login

# OpenCode Zen
echo 'export OPENCODE_API_KEY="your-key"' >> ~/.zshrc_envvars

# OpenRouter
echo 'export OPENROUTER_API_KEY="your-key"' >> ~/.zshrc_envvars
```

See platform-specific READMEs for detailed workflow documentation.

## License

MIT License - See individual configuration files for third-party licenses.

## Contributing

This is a personal dotfiles repository. Feel free to fork and adapt for your own use.
```
