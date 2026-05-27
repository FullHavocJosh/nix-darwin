# Nix-Darwin Cross-Platform Dotfiles

A comprehensive, declarative development environment configuration for **macOS** (using nix-darwin) and **Linux** (Arch/Omarchy), with powerful AI-assisted Git workflow automation.

## 🎯 What This Repository Provides

- **Declarative System Configuration** - Reproducible development environments across machines
- **Cross-Platform Support** - macOS (nix-darwin) and Linux (Arch/Omarchy)
- **AI-Powered Git Workflows** - Automated code review, commit messages, and PR generation
- **Multiple Profile Support** - Personal and work configurations with profile-specific packages
- **Complete Dev Environment** - Shell (zsh), editor (Neovim), terminal (tmux), window management, and more
- **Security-First Approach** - Smart gitignore patterns, secrets detection, environment variable management
- **Local LLM Integration** - llama.cpp server with Qwen2.5-Coder running as a launchd service
- **MCP Server Ecosystem** - Auto-registered Claude Code MCP servers for GitHub, Terraform, AWS, Slack, and more

## 📋 Quick Start

Choose your platform:

- **[macOS Setup Guide](README_MACOS.md)** - nix-darwin configuration for macOS
- **[Linux Setup Guide](README_LINUX.md)** - Arch Linux with Omarchy (Hyprland) desktop
- **[Omarchy Configuration Guide](README_OMARCHY.md)** - Detailed Hyprland/Omarchy customization

## 🏗️ Repository Structure

```
nix-darwin/
├── README.md                           # This file - Main documentation
├── README_MACOS.md                     # macOS-specific installation guide
├── README_LINUX.md                     # Linux-specific installation guide
├── README_OMARCHY.md                   # Omarchy (Hyprland) configuration details
├── flake.nix                           # Nix flake - Defines system profiles
├── .gitignore                          # Security-focused ignore patterns
├── .stow-local-ignore                  # Stow exclusions
│
├── nix-modules/macos/                  # macOS nix-darwin modules
│   ├── packages.nix                    # Shared packages (all profiles)
│   ├── config.nix                      # System configuration & scripts
│   ├── personal.nix                    # Personal profile packages/services
│   └── work.nix                        # Work profile packages/services
│
├── scripts/                            # Utility scripts
│   ├── truenas-smb-monitor.sh          # TrueNAS SMB service monitor
│   ├── install-nerd-fonts.sh          # Nerd Fonts installer
│   ├── setup-ssh-keys.sh               # SSH key setup automation
│   └── add-omarchy-themes-as-submodules.sh  # Omarchy theme manager
│
├── .config/                            # Application configurations (deployed via stow)
│   ├── aerospace/                      # AeroSpace (macOS tiling WM)
│   ├── alacritty/                      # Alacritty terminal config
│   ├── atuin/                          # Atuin shell history config
│   ├── btop/                           # btop system monitor
│   ├── ghostty/                        # Ghostty terminal config
│   ├── hypr/                           # Hyprland (Linux) configuration
│   ├── kitty/                          # Kitty terminal config
│   ├── mcp/                            # MCP server definitions (claude-desktop-mcp.json)
│   ├── nvim/                           # Neovim (LazyVim) configuration (incl. claudecode.nvim)
│   ├── opencode/                       # OpenCode AI assistant config
│   ├── superfile/                      # Superfile TUI file manager config
│   ├── tmux/                           # Tmux multiplexer config
│   ├── zed/                            # Zed editor config (gitignored - see security section)
│   └── ...                             # Many more application configs
│
├── .zshrc                              # Main zsh configuration
├── .zshrc_aliases                      # Shell aliases
├── .zshrc_functions_git                # Git workflow automation functions
├── .zshrc_functions_ai                 # AI provider selection & management
├── .zshrc_os_macos                     # macOS-specific shell config
├── .zshrc_os_linux                     # Linux-specific shell config
├── .zshrc_os_linux_omarchy_*           # Omarchy-specific shell config
├── .zshrc_envvars_insecure             # Non-sensitive environment variables (tracked)
└── .zshrc_envvars                      # Sensitive environment variables (gitignored)
```

## 🔐 Security Model

### Environment Variables Strategy

This repository uses a **two-file system** for environment variables:

1. **`.zshrc_envvars`** (gitignored) - **Sensitive credentials**
   - API keys (GitHub, OpenRouter, OpenCode)
   - Tokens and secrets
   - Personal access tokens
   - Created manually on each machine

2. **`.zshrc_envvars_insecure`** (tracked in git) - **Non-sensitive configuration**
   - Public settings
   - Tool configurations
   - Path settings
   - Safe to commit

### Zed Editor Configuration

The `.config/zed/settings.json` file is **gitignored** because it contains hardcoded tokens:

- GitHub Personal Access Token (for MCP server extension)
- AI conversation history
- Prompt database (unencrypted LMDB)

**Why gitignored?** Zed's MCP extension system does NOT support environment variable interpolation.

### Gitignore Patterns

See `.gitignore` for comprehensive patterns that protect:

- API keys and secrets
- SSH keys and certificates
- AWS credentials
- Ansible vault passwords
- Build artifacts
- Cache directories
- Editor session data

## 🎨 Platform Profiles

### macOS Profiles

Defined in `flake.nix`:

#### `macos_personal`

- Full personal development environment
- Gaming and entertainment apps (Steam, Battle.net, Whisky, Plex)
- Personal productivity tools (Obsidian, Proton Drive/Mail/VPN, Element)
- **Ollama** local LLM (runs as launchd service on `0.0.0.0:11434`)
- Custom wallpaper (set via activation script)
- User: `/Users/havoc`

#### `macos_work`

- Work-specific tools (Docker Desktop, Remote Desktop Manager Free)
- Enterprise apps (Citrix Workspace, LastPass, MQTT Explorer, PowerShell)
- Kubernetes tools (k9s, kubectl, act)
- **Terraform cache cleanup** on activation (cleans `.terraform` directories under `~/pscloudops/terraform-infrastructure`)
- User: `/Users/jrollet`

#### Shared (all macOS profiles, via `packages.nix`)

- **llama-server** launchd service — runs Qwen2.5-Coder-7B-Q8 via llama.cpp on `127.0.0.1:8080`; model auto-downloaded on activation

**Switch profiles:**

```bash
darwin-rebuild switch --flake ~/nix-darwin#macos_personal
darwin-rebuild switch --flake ~/nix-darwin#macos_work
```

### Linux (Omarchy)

Single profile focused on personal development and desktop environment.

- Full Hyprland desktop (managed by Omarchy)
- Manual package installation (pacman, AUR, flatpak, cargo, npm, go)
- Deployed via GNU Stow
- See [README_LINUX.md](README_LINUX.md) for details

## 🤖 AI-Powered Git Workflow

This repository includes powerful shell functions for AI-assisted development.

### AI Provider Selection

Configure which AI provider to use:

```bash
aiselect              # Interactive menu
aiselect --show       # Show current provider
```

**Supported providers:**

- **Claude Code** - Anthropic Claude via Claude Code subscription
- **GitHub Copilot** - Requires `gh auth login`
- **OpenCode** - Requires `OPENCODE_API_KEY` in `~/.zshrc_envvars`
- **OpenRouter** - Requires `OPENROUTER_API_KEY` in `~/.zshrc_envvars`
- **llama.cpp** - Local inference via the managed llama-server launchd service (no API key required)

### Key Git Functions

#### `gpa` - Git Partial Add with AI Review

Interactive staging with comprehensive checks:

1. **Secrets detection** - Scans for API keys, passwords, tokens
2. **Linting** - Auto-runs nixfmt, prettier, ruff on staged files
3. **Batched AI review** - Reviews code in ~300 line batches
4. **Interactive fixes** - Edit issues with AI assistance in tmux workspace

```bash
gpa                   # Select files, lint, and get AI code review
```

#### `gpc` - Git Push with Commit (AI-generated message)

Automatically generates conventional commit messages:

```bash
gpc                   # AI generates commit message and pushes
gpc --skip-readme     # Skip README update check
```

#### `gpr_func` - Git Pull Request

Creates draft PR with auto-generated README if missing:

```bash
gpr_func              # Interactive PR creation with AI-generated description
```

#### `aidev` - Launch AI Development Assistant

```bash
aidev                 # Start OpenCode with selected provider
aidev --model <model> # Override model selection
```

### Required Packages

All automatically installed via nix-darwin/package managers:

- `jq` - JSON parsing
- `nixfmt` - Nix formatter
- `prettier` - Multi-language formatter
- `ruff` - Python linter
- `opencode` - AI code assistant
- `llama.cpp` (`llama-server`) - Local LLM inference
- `gh` - GitHub CLI
- `tmux` - Terminal multiplexer
- `neovim` - Text editor

## 🤖 Claude Code & MCP Integration

`config.nix` automatically sets up Claude Code on activation:

- **Skills symlink** — `~/.claude/skills` → `~/nix-darwin/.claude/skills`
- **Settings symlink** — `~/.claude/settings.local.json` → `~/nix-darwin/.claude/settings.local.json`
- **MCP server auto-registration** — reads `~/.config/mcp/claude-desktop-mcp.json` and registers all servers via `claude mcp add`
- **Custom MCP servers** — any `~/mcp-*/` directory with a `package.json` is auto-built and registered

### MCP Servers (`.config/mcp/claude-desktop-mcp.json`)

| Server                   | Description                                                     |
| ------------------------ | --------------------------------------------------------------- |
| `context-guardian`       | Custom local MCP server (`~/mcp-context-guardian-fullhavoc`)    |
| `memory`                 | `@modelcontextprotocol/server-memory` — persistent entity graph |
| `sequential-thinking`    | `@modelcontextprotocol/server-sequential-thinking`              |
| `github`                 | `@edjl/github-mcp` — GitHub PR/issue integration                |
| `terraform`              | `terraform-mcp-server` — Terraform registry docs                |
| `context7`               | `@upstash/context7-mcp` — up-to-date library documentation      |
| `aws-core-mcp-server`    | `awslabs.core-mcp-server` — AWS service proxy/orchestration     |
| `aws-terraform-mcp`      | `awslabs.terraform-mcp-server` — AWS Terraform provider docs    |
| `aws-pricing-mcp-server` | `awslabs.aws-pricing-mcp-server` — AWS pricing API              |
| `mcp-server-chart`       | `@antv/mcp-server-chart` — chart/diagram generation             |
| `slack`                  | `@modelcontextprotocol/server-slack` — Slack integration        |

### Neovim Claude Code Plugin

`claudecode.nvim` (`coder/claudecode.nvim`) is installed via LazyVim with vertical diff layout.

---

## 🛠️ Development Tools

### Editors & IDEs

- **Neovim** - Primary editor (LazyVim configuration, with `claudecode.nvim`)
- **Neovide** - GPU-accelerated Neovim GUI
- **Zed** - Modern collaborative editor (with nixd/nil LSP)
- **Sublime Text** - GUI text editor
- **GoLand** - JetBrains Go IDE (macOS)

### Terminals

- **Alacritty** - GPU-accelerated terminal
- **Ghostty** - Modern terminal emulator
- **Kitty** - Feature-rich terminal

### Window Management

- **AeroSpace** - macOS tiling window manager
- **Hyprland** - Linux Wayland compositor (via Omarchy)

### Shell

- **Zsh** - Shell with extensive customization
- **Starship** - Cross-shell prompt
- **Atuin** - Shell history database
- **Zinit** - Zsh plugin manager
- **Zoxide** - Smart directory jumping

### Version Control

- **Git** - Version control
- **GitHub CLI** (`gh`) - GitHub integration
- **Lazygit** - Terminal UI for Git

### Languages & Runtimes

- **Go** - Go toolchain
- **Rust** - Rust toolchain (rustc, cargo)
- **Node.js** - JavaScript runtime (v24 LTS)
- **Python** - Python 3 with pip
- **Ruby** - Ruby with gem

### Cloud & Infrastructure

- **AWS CLI** - AWS command-line interface
- **Terraform** (`tofu`) - Infrastructure as Code
- **Ansible** - Configuration management
- **Docker** - Containerization

### System Monitoring & File Management

- **btop** - Resource monitor
- **htop** - Process viewer
- **k9s** - Kubernetes TUI
- **superfile** - TUI file manager

## 📦 Package Management

### macOS (nix-darwin)

**Find packages:**

```bash
nix search nixpkgs <package-name>
```

Visit [search.nixos.org](https://search.nixos.org)

**Add packages:**

1. Edit `nix-modules/macos/packages.nix` (shared across profiles)
2. Or edit `nix-modules/macos/personal.nix` or `work.nix` (profile-specific)

**Update packages:**

```bash
nix flake update
darwin-rebuild switch --flake ~/nix-darwin#macos_personal
```

### Linux (Arch/Omarchy)

**Package managers:**

- `pacman` - Official Arch packages
- `yay` - AUR helper
- `flatpak` - Sandboxed GUI apps
- `cargo` - Rust crates
- `npm` - Node.js packages
- `go install` - Go tools
- `pipx` - Isolated Python tools

See [README_LINUX.md](README_LINUX.md) for installation commands.

## 🚀 Deployment with GNU Stow

This repository uses **GNU Stow** for dotfile management, creating symlinks from `~/.config/` to `~/nix-darwin/.config/`.

**Deploy all dotfiles:**

```bash
cd ~/nix-darwin
stow . -t ~
```

**Deploy specific directory:**

```bash
stow .config -t ~
```

**Remove (unstow):**

```bash
stow -D . -t ~
```

### Stow Ignore Patterns

`.stow-local-ignore` excludes files from stowing:

- `.git/` - Git repository files
- `nix-modules/` - Nix configuration (not dotfiles)
- `scripts/` - Utility scripts (not dotfiles)
- `README*.md` - Documentation
- `.gitignore` - Git configuration
- Other non-dotfile directories

## 🔧 Troubleshooting

### macOS Issues

**Homebrew paths not found:**

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
```

**AeroSpace permissions:**

- Grant Accessibility permissions in System Settings → Privacy & Security

**nix-darwin errors:**

```bash
darwin-rebuild switch --flake ~/nix-darwin#macos_personal --show-trace
```

**Zed LSP issues:**

- Ensure absolute paths in `~/.config/zed/settings.json`:
  - `"path": "/run/current-system/sw/bin/nixd"`
  - `"command": ["/opt/homebrew/bin/nixfmt"]`

### Linux Issues

**Missing commands:**

```bash
export PATH="$HOME/.local/bin:$HOME/go/bin:$HOME/.cargo/bin:$HOME/.npm-global/bin:$PATH"
```

**Zinit not loading:**

```bash
git clone https://github.com/zdharma-continuum/zinit.git ~/.local/share/zinit/zinit.git
```

**Tmux plugins not installed:**

- Press `Prefix + I` in tmux

**Hyprland not starting:**

- Ensure you're using Wayland, not X11
- Check `~/.config/hypr/hyprland.conf`

## 🔄 Updating This Configuration

### Pull Latest Changes

```bash
cd ~/nix-darwin
git pull
```

### macOS: Apply Updates

```bash
nix flake update
darwin-rebuild switch --flake ~/nix-darwin#macos_personal
```

### Linux: Re-Stow Dotfiles

```bash
cd ~/nix-darwin
stow -R . -t ~  # Re-stow (replaces existing symlinks)
```

### Update Omarchy Themes

```bash
cd ~/nix-darwin
git submodule update --remote --merge
```

## 📚 Additional Documentation

- **[macOS Setup Guide](README_MACOS.md)** - Detailed macOS installation steps
- **[Linux Setup Guide](README_LINUX.md)** - Complete Linux/Omarchy setup
- **[Omarchy Configuration](README_OMARCHY.md)** - Hyprland customization details
- **[TrueNAS SMB Monitor](scripts/README_TRUENAS.md)** - TrueNAS service monitoring

## 🤝 Contributing

This is a personal dotfiles repository, but feel free to:

- Open issues for questions or bugs
- Submit PRs for improvements
- Fork and customize for your own use

## 📄 License

This repository is provided as-is for personal and educational use.

## 🙏 Acknowledgments

- [nix-darwin](https://github.com/LnL7/nix-darwin) - macOS system configuration
- [Omarchy](https://omarchy.org) - Hyprland-based desktop environment
- [LazyVim](https://www.lazyvim.org/) - Neovim configuration framework
- [GNU Stow](https://www.gnu.org/software/stow/) - Symlink farm manager

---

**Repository:** [FullHavocJosh/nix-darwin](https://github.com/FullHavocJosh/nix-darwin)  
**Author:** Josh Rollet (havoc)  
**Last Updated:** April 15, 2026
