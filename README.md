# Nix-Darwin Cross-Platform Dotfiles

A comprehensive, declarative development environment configuration for **macOS** (using nix-darwin), with powerful AI-assisted Git workflow automation.

## 🎯 What This Repository Provides

- **Declarative System Configuration** - Reproducible development environments across machines
- **Cross-Platform Support** - macOS (nix-darwin) and Linux
- **AI-Powered Git Workflows** - Automated code review, commit messages, and PR generation
- **Multiple Profile Support** - Personal and work configurations with profile-specific packages
- **Complete Dev Environment** - Shell (zsh), editor (Neovim), terminal (herdr), window management, and more
- **Security-First Approach** - Smart gitignore patterns, secrets detection, environment variable management
- **Local LLM Integration** - LM Studio (Qwen3.5-9B) served on localhost, kept running by a launchd daemon
- **MCP Server Ecosystem** - Auto-registered Claude Code MCP servers for GitHub, Terraform, AWS, Slack, and more

## 📋 Quick Start

Choose your platform:

- **[macOS Setup Guide](README_MACOS.md)** - nix-darwin configuration for macOS

## 🏗️ Repository Structure

```
nix-darwin/
├── README.md                           # This file - Main documentation
├── README_MACOS.md                     # macOS-specific installation guide
├── flake.nix                           # Nix flake - Defines system profiles
├── .gitignore                          # Security-focused ignore patterns
├── .stow-local-ignore                  # Stow exclusions
│
├── nix-modules/macos/                  # macOS nix-darwin modules
│   ├── packages-tui.nix                # Shared CLI packages (all profiles)
│   ├── packages-gui.nix                # Shared GUI apps (laptop/work profiles)
│   ├── packages-laptop-only.nix        # Laptop-only packages
│   ├── config.nix                      # System configuration & scripts
│   ├── personal.nix                    # Personal (laptop/desktop) profile packages/services
│   ├── work.nix                        # Work profile packages/services
│   ├── laptop.nix                      # Laptop-specific config
│   └── desktop.nix                     # Desktop-specific config
│
├── scripts/                            # Utility scripts
│   ├── truenas-smb-monitor.sh          # TrueNAS SMB service monitor
│   ├── install-nerd-fonts.sh          # Nerd Fonts installer
│   └── setup-ssh-keys.sh               # SSH key setup automation
│
├── .config/                            # Application configurations (deployed via stow)
│   ├── aerospace/                      # AeroSpace (macOS tiling WM)
│   ├── atuin/                          # Atuin shell history config
│   ├── btop/                           # btop system monitor
│   ├── ghostty/                        # Ghostty terminal config
│   ├── kitty/                          # Kitty terminal config
│   ├── mcp/                            # MCP server definitions (claude-desktop-mcp.json)
│   ├── nvim/                           # Neovim (LazyVim) configuration (incl. claudecode.nvim)
│   ├── opencode/                       # OpenCode AI assistant config
│   ├── superfile/                      # Superfile TUI file manager config
│   ├── herdr/                          # herdr terminal workspace manager config
│   ├── zed/                            # Zed editor config (gitignored - see security section)
│   └── ...                             # Many more application configs
│
├── .zshrc                              # Main zsh configuration
├── .zshrc_aliases                      # Shell aliases
├── .zshrc_functions_git                # Git workflow automation functions
├── .zshrc_functions_ai                 # AI provider selection & management
├── .zshrc_os_macos                     # macOS-specific shell config
├── .zshrc_os_linux                     # Linux-specific shell config
├── .zshrc_os_linux_omarchy_*           # Linux shell configs
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

#### `macos_laptop`

- Full personal development environment, laptop-specific packages (`packages-laptop-only.nix`)
- Gaming and entertainment apps (Steam, Battle.net, Whisky, Plex)
- Personal productivity tools (Obsidian, Proton Drive/Mail/VPN, Element)
- Local LLM via LM Studio (`lmstudio.nix`)
- Custom wallpaper (set via activation script)
- User: `/Users/havoc`

#### `macos_desktop`

- Personal development environment (no laptop-only packages, no GUI app bundle)
- Local LLM via LM Studio (`lmstudio.nix`) plus Ollama for the AzerothCore bot chat (`desktop.nix`)
- User: `/Users/havoc`

#### `macos_work`

- Work-specific tools (Docker Desktop, Remote Desktop Manager Free)
- Enterprise apps (Citrix Workspace, LastPass, MQTT Explorer, PowerShell)
- Kubernetes tools (k9s, kubectl, act)
- **Terraform cache cleanup** on activation (cleans `.terraform` directories under `~/pscloudops/terraform-infrastructure`)
- User: `/Users/jrollet`

#### Shared (all macOS profiles, via `packages-tui.nix`)

- **LM Studio** launchd daemon (`lmstudio.nix`) — runs LM Studio headless (`--run-as-service`) on `localhost:1234`; `qwen/qwen3.5-9b` is used for gpc/gpa/gpr and aistack tier 1, and the provisioner downloads whichever models in its list fit the host's RAM

#### aistack (planner-led coding stack)

`aistack make a new mcp server` (or `aistack`, then type it in pi) opens a live pi session on the local LM Studio
model. It drafts a plan (`prd.json` and `verify.json`) with you, and only after you confirm the plan runs it. Nothing
aistack-related is written into the repository (no `.aistack/`, no `.ralph-tui/`): plan files, runs, questions,
reviews, progress notes and Ralph's own state live in `~/.aistack/<project>-<hash>/` (`AISTACK_HOME` overrides the
base). Planning only reads the project. In the main checkout of a git repo the git worktree and draft PR are created
at the moment you confirm the plan (`ralph_run` does it), and the agents work there; in an existing worktree or a
non-git directory they work in place. A later run reuses the worktree while it exists. The tiers:

- tier 0: planning. Lumo on MacMiniM1 drafts the task breakdown (`lumo_consult`); if MacMiniM1 is unreachable at
  launch (probed with a 4 s timeout), or Lumo fails mid-session, the local `qwen/qwen3.5-9b` plans instead. pi + LM
  Studio stays the coordinator either way (it talks to you and calls the `ralph_*` tools, which Lumo cannot do)
- tier 1: OpenCode Big Pickle (free Zen model) builds each task (Claude Sonnet instead when the host has no OpenCode
  Zen key; another free model with a notice if Big Pickle is not available)
- tier 2: Claude Code Sonnet (the `sonnet` alias, always the latest Sonnet) takes over a task tier 1 cannot get to
  pass, and reviews the result read-only for security, accuracy and completeness

`AISTACK_TIER0=local` forces the local planner; the banner shows which tier 0 was chosen.

Migrating from the old layout: earlier versions kept `.aistack/` and `.ralph-tui/` inside the project, and in this
dotfiles repo stow even linked them into `$HOME` (`~/.aistack -> nix-darwin/.aistack`). `.stow-local-ignore` now
ignores both, but the existing links and directories have to be removed by hand once (they only hold old plans and
run logs): `rm ~/.aistack ~/.ralph-tui && rm -rf ~/nix-darwin/.aistack ~/nix-darwin/.ralph-tui`. aistack refuses to
start while `~/.aistack` resolves inside a git repository.

The run is `.config/aistack/ralph_driver.py` (detached, state in `~/.aistack/<project>/runs/`), driving
[Ralph TUI](https://ralph-tui.com) one task at a time. A task counts as done only when its `verify.json` commands
exit 0, because Ralph's own completion marker can be a false positive. pi reaches the run through the MCP tools in
`.config/aistack/ralph_mcp.py`. Ralph itself runs from `~/.aistack/<project>/ralph` (it keeps its session files in
its working directory) and the agent wrappers (`claude-work.sh`, `claude-review.sh`, `opencode-auto.sh`) `cd` into the
work directory first; the reviewer may write only to `~/.aistack/<project>/reviews`. Under herdr `gpr` leaves the
pane where it is, so the worktree path is computed from the branch name (`.worktrees/<branch>`). Nothing is
committed; use `gpc`/`gpa` in the work directory afterwards. Tests: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_driver.py`.

#### Lumo tier 0 (cloud planner, `macos_desktop` only)

Proton Lumo as a tool-less planning model, hosted on MacMiniM1 (`nix-modules/macos/lumo.nix`, scripts in
`.config/lumo/`). Three LaunchDaemons run as `havoc`, so nothing needs a login session:

- `lumo-tamer`: [lumo-tamer](https://github.com/ZeroTricks/lumo-tamer), an **unofficial** OpenAI-compatible server
  for Lumo (port 3003, API key). Pinned to one reviewed commit and built by an activation-time provisioner.
  Using it may violate Proton's terms of service (its README says so).
- `lumo-planner`: `.config/lumo/lumo_planner.py`, a stdlib proxy (port 8765). Lumo cannot call tools, so it is
  told to end replies with `NEED:` lines (a path, `ls`, `find`, `grep`, or keywords); the proxy answers them from
  `~/home-infrastructure` and loops until Lumo gives a final plan. No local model is involved. A name-based deny
  list (`.env`, keys, tfvars, kubeconfig, `*secret*`, ...) is enforced in code. It listens beyond loopback only
  when Doppler holds `LUMO_PLANNER_API_KEY` (bearer token), and refuses to otherwise. The macOS application
  firewall also has to allow its interpreter: `lumo.nix` adds Homebrew's `Python.app` to it on every activation.
  tamer (node) is deliberately left blocked, because only the planner talks to it, on loopback.
- `lumo-watchdog` (every 5 min): checks `tamer auth status`, the server, and every 30 min a real one-word Lumo
  request; alerts through ntfy on failure and on recovery; optionally re-authenticates by itself.

`lumoplan` opens a tool-less pi session on it (`pi --no-tools ... --provider lumo-planner`). That mode can only
read the Mini's `home-infrastructure` checkout, which is all the proxy serves.

Inside `aistack`, tier 0 consults Lumo through the `lumo_consult` tool in
`.config/aistack/ralph_mcp.py`: for larger requests the planner sends the request plus a few project files to
Lumo and gets a draft task breakdown back, which it adapts into `prd.json`/`verify.json` itself (still validated
and confirmed by you). Because the proxy cannot see aistack projects, the files are sent inline, only ones the
planner lists, never secrets/keys/env files (same deny list as the proxy), at most 12 files and 60 KB, and the
proxy is told not to fetch anything (`X-Lumo-No-Fetch: 1`). If Lumo is unreachable the tool returns ok=false and
planning continues without it. The key comes from Doppler `LUMO_PLANNER_API_KEY`; `AISTACK_LUMO_URL` overrides
the endpoint.

Doppler `FullHavocJosh/root_macmini` (all optional, daemons fall back to local files):
`LUMO_VAULT_KEY` (restores a _missing_ key file only), `LUMO_TAMER_API_KEY`, `LUMO_PLANNER_API_KEY`,
`LUMO_NTFY_URL` (full topic URL), `LUMO_NTFY_TOKEN` (ntfy access token).

First setup and every re-auth: run `lumoreauth` on the MacBook (`.config/lumo/reauth.sh`). The Mini is headless, so the
sign-in happens here: it opens Chromium with a temporary profile, you sign in to Lumo (Proton shows CAPTCHA and 2FA),
and it runs `tamer auth browser` on the Mini through an SSH reverse tunnel to that browser, restarts tamer and shows
the auth status. The profile is deleted on exit, because lumo-tamer's docs say not to reuse the same tokens on two
machines. `lumoreauth --check` tests everything except the handover (Chromium starts, the tunnel carries its debug
port) and changes nothing on the Mini. When auth fails, the watchdog's ntfy alert tells you to run it. Fully automatic
re-auth is not possible while a CAPTCHA/2FA sign-in is required.

(The watchdog still has an opt-in headless re-auth for a Chromium profile signed in on the Mini itself
(`~/.lumo-chromium` plus `~/.lumo-watchdog/auto-reauth`). It needs a GUI session on the Mini, so it is unused.)

The MacBook has no tamer of its own: pi's `lumo-planner` provider (planner proxy, port 8765) and `lumo` provider
(tamer directly, port 3003) both point at the Mini. Both need Doppler `LUMO_PLANNER_API_KEY` / `LUMO_TAMER_API_KEY`.
`lumo.nix` allows the Mini's Python and node through the application firewall for this; both are protected by
their API keys only, so keep them to the LAN.

Moving from a hand-made setup: remove `~/Library/LaunchAgents/com.fullhavoc.lumo-*.plist` (launchctl bootout
`gui/501/com.fullhavoc.lumo-tamer` and `-planner`) before the first `darwin-rebuild switch`, or both fight for the ports.

**Switch profiles:**

```bash
darwin-rebuild switch --flake ~/nix-darwin#macos_laptop
darwin-rebuild switch --flake ~/nix-darwin#macos_desktop
darwin-rebuild switch --flake ~/nix-darwin#macos_work
```

### Linux

Single profile focused on personal development and desktop environment.

- Deployed via GNU Stow

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
- **LM Studio** - Local inference via the managed LM Studio daemon (no API key required)

### Key Git Functions

#### `gpa` - Git Partial Add with AI Review

Interactive staging with comprehensive checks:

1. **Secrets detection** - Scans for API keys, passwords, tokens
2. **Linting** - Auto-runs nixfmt, prettier, ruff on staged files
3. **Batched AI review** - Reviews code in ~300 line batches
4. **Interactive fixes** - Edit issues with AI assistance in herdr workspace

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
- LM Studio (cask) - Local LLM inference
- `gh` - GitHub CLI
- `herdr` - Terminal workspace manager
- `neovim` - Text editor

## 🤖 Claude Code & MCP Integration

`config.nix` automatically sets up Claude Code on activation:

- **Skills symlink** — `~/.claude/skills` → `~/nix-darwin/.claude/skills`
- **Settings symlink** — `~/.claude/settings.local.json` → `~/nix-darwin/.claude/settings.local.json`
- **MCP server auto-registration** — reads `~/.config/mcp/claude-desktop-mcp.json` and registers all servers via `claude mcp add`
- **Custom MCP servers** — any `~/mcp-*/` directory with a `package.json` is auto-built and registered

### MCP Servers (`.config/mcp/claude-desktop-mcp.json`)

| Server                   | Description                                                                                                                   |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `context-guardian`       | Custom local MCP server (`~/mcp-context-guardian-fullhavoc`)                                                                  |
| `verbosity-guardian`     | Custom local MCP server (`~/mcp-verbosity-guardian`) — flags verbose/redundant code comments, PR/ticket text, commit messages |
| `memory`                 | `@modelcontextprotocol/server-memory` — persistent entity graph                                                               |
| `sequential-thinking`    | `@modelcontextprotocol/server-sequential-thinking`                                                                            |
| `github`                 | `@edjl/github-mcp` — GitHub PR/issue integration                                                                              |
| `terraform`              | `terraform-mcp-server` — Terraform registry docs                                                                              |
| `context7`               | `@upstash/context7-mcp` — up-to-date library documentation                                                                    |
| `aws-core-mcp-server`    | `awslabs.core-mcp-server` — AWS service proxy/orchestration                                                                   |
| `aws-terraform-mcp`      | `awslabs.terraform-mcp-server` — AWS Terraform provider docs                                                                  |
| `aws-pricing-mcp-server` | `awslabs.aws-pricing-mcp-server` — AWS pricing API                                                                            |
| `mcp-server-chart`       | `@antv/mcp-server-chart` — chart/diagram generation                                                                           |
| `slack`                  | `@modelcontextprotocol/server-slack` — Slack integration                                                                      |

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

- **Ghostty** - Fast, native GPU-accelerated terminal
- **Kitty** - Feature-rich terminal

### Window Management

- **AeroSpace** - macOS tiling window manager
- **Hyprland** - Linux Wayland compositor

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

1. Edit `nix-modules/macos/packages-tui.nix` (CLI, shared across all profiles) or `packages-gui.nix` (GUI apps, shared by laptop/work) or `packages-laptop-only.nix` (laptop only)
2. Or edit `nix-modules/macos/personal.nix` or `work.nix` (profile-specific)

**Update packages:**

```bash
nix flake update
darwin-rebuild switch --flake ~/nix-darwin#macos_laptop
```

### Linux

Package management depends on the distribution.

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
darwin-rebuild switch --flake ~/nix-darwin#macos_laptop --show-trace
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

**Tmux plugins not installed:**

- Press `Prefix + I` in tmux

## 🔄 Updating This Configuration

### Pull Latest Changes

```bash
cd ~/nix-darwin
git pull
```

### macOS: Apply Updates

```bash
nix flake update
darwin-rebuild switch --flake ~/nix-darwin#macos_laptop
```

### Linux: Re-Stow Dotfiles

```bash
cd ~/nix-darwin
stow -R . -t ~  # Re-stow (replaces existing symlinks)
```

## 📚 Additional Documentation

- **[macOS Setup Guide](README_MACOS.md)** - Detailed macOS installation steps
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

- [LazyVim](https://www.lazyvim.org/) - Neovim configuration framework
- [GNU Stow](https://www.gnu.org/software/stow/) - Symlink farm manager

---

**Repository:** [FullHavocJosh/nix-darwin](https://github.com/FullHavocJosh/nix-darwin)  
**Author:** Josh Rollet (havoc)  
**Last Updated:** April 15, 2026
