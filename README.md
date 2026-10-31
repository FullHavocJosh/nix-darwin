# Nix-Darwin Cross-Platform Dotfiles

A comprehensive, declarative development environment configuration for **macOS** (using nix-darwin), with powerful AI-assisted Git workflow automation.

## 🎯 What This Repository Provides

- **Declarative System Configuration** - Reproducible development environments across machines
- **Cross-Platform Support** - macOS (nix-darwin) and Linux
- **AI-Powered Git Workflows** - Automated code review, commit messages, and PR generation
- **Multiple Profile Support** - Personal and work configurations with profile-specific packages
- **Complete Dev Environment** - Shell (zsh), editor (Neovim), terminal (tuios), window management, and more
- **Security-First Approach** - Smart gitignore patterns, secrets detection, environment variable management
- **Local LLM Integration** - llama.cpp (Qwen3.5-9B) served on 127.0.0.1 only, kept running by a launchd daemon
- **CI** - GitHub Actions (`.github/workflows/validate.yml`) evaluates every darwin configuration, runs shellcheck and gitleaks
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
│   ├── packages-devtest.nix            # Laptop only: browser engines, simulator tooling, VMs
│   ├── config.nix                      # System configuration & scripts
│   ├── personal.nix                    # Personal (laptop/desktop) profile packages/services
│   ├── work.nix                        # Work profile packages/services
│   ├── laptop.nix                      # Laptop-specific config
│   ├── desktop.nix                     # Desktop-specific config
│   ├── llamacpp-local.nix              # llama-server launchd daemon
│   ├── lumo.nix                        # lumo-tamer daemons
│   ├── timemachine-exclusions.nix      # applies timemachine-exclusions.txt, laptop and desktop
│   └── claude-tui-usage-patch.py       # idempotent patch of the claude-tui brew formula, run on activation
│
├── scripts/                            # Utility scripts
│   ├── truenas-smb-monitor.sh          # TrueNAS SMB service monitor
│   ├── install-nerd-fonts.sh           # Nerd Fonts installer
│   ├── setup-ssh-keys.sh               # SSH key setup automation
│   ├── check-timemachine-exclusions.sh # validates timemachine-exclusions.txt
│   └── opnsense-routing.sh             # routing fix after plugging in the OPNsense LAN cable
│
├── .config/                            # Application configurations (deployed via stow)
│   ├── aerospace/                      # AeroSpace (macOS tiling WM)
│   ├── aistack/                        # aidev and gpa helpers, MCP servers for local-edit and oczen
│   ├── aistack-tuios/                  # aidev on tuios: aidev_tuios.py
│   ├── atuin/                          # Atuin shell history config
│   ├── btop/                           # btop system monitor
│   ├── ghostty/                        # Ghostty terminal config
│   ├── lumo/                           # lumo-tamer scripts and Lumo MCP
│   ├── mcp/                            # MCP server definitions (claude-desktop-mcp.json)
│   ├── nvim/                           # Neovim (LazyVim) configuration (incl. claudecode.nvim)
│   ├── opencode/                       # OpenCode AI assistant config
│   ├── pi/                             # pi config
│   ├── superfile/                      # Superfile TUI file manager config
│   ├── tuios/                          # tuios config.toml
│   └── ...                             # Many more application configs
│
├── .zshrc                              # Main zsh configuration
├── .zshrc_aliases                      # Shell aliases
├── .zshrc_functions_git                # Git workflow automation functions
├── .zshrc_functions_ai                 # AI provider selection & management
├── .zshrc_functions_tuios              # tuios session and aidev commands
├── .zshrc_os_macos                     # macOS-specific shell config
├── .zshrc_os_linux                     # Linux-specific shell config
├── .zshrc_os_linux_omarchy_*           # Linux shell configs
├── .zshrc_envvars_insecure             # Non-sensitive environment variables (tracked)
├── .github/workflows/validate.yml      # GitHub Actions workflow
├── timemachine-exclusions.txt          # Time Machine exclusions
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
- Local LLM via llama.cpp (`llamacpp-local.nix`)
- Test targets for web, mobile and native work (`packages-devtest.nix`): browser engines, Xcode and simulator tooling, Linux/macOS VMs
- Time Machine exclusions from `timemachine-exclusions.txt` (`timemachine-exclusions.nix`)
- Custom wallpaper (set via activation script)
- User: `/Users/havoc`

#### `macos_desktop`

- Personal development environment (no laptop-only packages, no GUI app bundle)
- Local LLM via llama.cpp (`llamacpp-local.nix`) plus Ollama for the AzerothCore bot chat (`desktop.nix`)
- Time Machine exclusions from `timemachine-exclusions.txt` (`timemachine-exclusions.nix`)
- User: `/Users/havoc`

#### `macos_work`

- Work-specific tools (Docker Desktop, Remote Desktop Manager Free)
- Enterprise apps (Citrix Workspace, LastPass, MQTT Explorer, PowerShell)
- Kubernetes tools (k9s, kubectl, act)
- **Terraform cache cleanup** on activation (cleans `.terraform` directories under `~/pscloudops/terraform-infrastructure`)
- User: `/Users/jrollet`

#### Shared (all macOS profiles, via `packages-tui.nix`)

- **llama-server** launchd daemon: serves `qwen/qwen3.5-9b` (Qwen3.5-9B Q4_K_M GGUF, 128K context) on `127.0.0.1:8080` only; the bind address is hard-coded and `_validate_llamacpp` rejects any other `LLAMA_CPP_HOST`. Used for gpc/gpa/gpr and opencode. The GGUF is downloaded to `~/models` (sha256-verified) on `darwin-rebuild switch`. No LM Studio, no LM Link: no device calls another device's model.

#### Lumo (lumo-tamer, on every personal Mac)

Proton Lumo as a tool-less drafting model for `aidev` (`nix-modules/macos/lumo.nix`, scripts in `.config/lumo/`). Each host runs
its own copy, with its own keys and its own Proton sign-in; `local.lumo.lan` in `flake.nix` decides who may reach it:

|                      | `macos_desktop` (MacMiniM1, `lan = true`)            | `macos_laptop` (`lan = false`, the default) |
| -------------------- | ---------------------------------------------------- | ------------------------------------------- |
| tamer :3003          | every device on the network, behind its API key      | `127.0.0.1` only                            |
| application firewall | node (tamer) is allowed in                           | not touched                                 |
| tamer and vault keys | Doppler `root_macmini`                               | generated and kept on the host              |
| sign-in              | `lumoreauth` from the MacBook (the Mini is headless) | `lumoauth` on the laptop itself             |

Upstream lumo-tamer has no setting for its listen address, so the fork's one `listen()` call reads `LUMO_TAMER_HOST`
(unset means every interface); `run-tamer.sh` sets it to `127.0.0.1` on a loopback host and refuses to start a build
without it. `darwin-reload switch laptop|desktop` (`.zshrc_aliases`) runs `sudo darwin-rebuild switch` for that host (the
desktop's over ssh when called from the MacBook) and then starts the browser sign-in if that host's Proton session is
not valid: `lumoauth` for the laptop, `lumoreauth` for the Mini. A valid session is left alone. Plain
`darwin-rebuild switch` only prints the sign-in state.
`aidev` uses this machine's own Lumo when it answers, then the Mini's, then `https://lumo.rollet.family/v1`.

What follows describes the daemons. Two LaunchDaemons run as `havoc`, so nothing needs a login session:

- `lumo-tamer`: [lumo-tamer](https://github.com/ZeroTricks/lumo-tamer), an **unofficial** OpenAI-compatible server
  for Lumo (port 3003, API key). Pinned to one reviewed commit and built by an activation-time provisioner.
  Using it may violate Proton's terms of service (its README says so).
- `lumo-watchdog` (every 5 min): checks `tamer auth status`, the server on loopback and (on the Mini) on its network
  address, and every 30 min a real one-word Lumo request; restarts tamer when a server check fails (at most every 15
  min); alerts through ntfy when that does not fix it, on any other failure and on recovery; optionally re-authenticates
  by itself.

A switch that upgrades Homebrew's node also restarts tamer: on the removed binary it would still answer on loopback but
not on the network.

There used to be a third daemon, `lumo-planner` (port 8765), a proxy that ran this loop against one fixed repository,
and a `lumoplan` command that used it. Both are removed.

Doppler `FullHavocJosh/root_macmini`, read on the desktop only (all optional):
`LUMO_VAULT_KEY` (restores a _missing_ key file only), `LUMO_TAMER_API_KEY`,
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

The MacBook runs its own tamer on loopback. pi's `lumo` provider still points at the Mini's tamer (port 3003, Doppler
`LUMO_TAMER_API_KEY`). `lumo.nix` allows the Mini's node through the application firewall for this; tamer is protected
by its API key only, so keep it to the LAN.

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

## Terminal: tuios

tuios is the daily terminal multiplexer, installed by brew (`packages-tui.nix`), config in `.config/tuios/config.toml`, commands in `.zshrc_functions_tuios`.

| Command                            | What it does                                                                               |
| ---------------------------------- | ------------------------------------------------------------------------------------------ |
| `dev`                              | reattach the daemon's sessions; with none, create nix-darwin, terraform-infrastructure and |
|                                    | home-infrastructure where cloned. Layout: workspace `dev` nvim + aidev's Claude, `ai` Lumo |
| `devim [name]`                     | that layout for the current directory, always a new session                                |
| `nxvim`, `psvim`, `hivim`, `itvim` | the session of one project, skipped where it is not cloned                                 |
| `hiwt <branch>`                    | a new home-infrastructure worktree and branch in `.worktrees/`, with a session of its own  |
| `peerdev <session>`                | a session on the peer Mac through tuios host link                                          |
| `nxpeer`, `hipeer`                 | peerdev for nix-darwin and home-infrastructure sessions                                    |
| `mmdev`, `himmdev`, `nxmmdev`      | old names, kept as aliases of `peerdev`, `hipeer`, `nxpeer`                                |
| `ai_tuios [-c] [message]`          | one Claude Code pane in session `ai_tuios-<dir>` (`-c` continues the last one here)        |

Review: `ctrl+t v` opens the tuios review view of the focused pane's changes, against the branch's upstream (a pushed
`gpr` branch shows only unpushed and uncommitted work). `c` notes a line, `C` a hunk, `S` sends the notes to the pane's
agent. `prdiff` prints the whole PR's diff against origin's default branch.

Run them from a plain Ghostty window. Keys (`.config/tuios/config.toml`): `ctrl+t` is tuios's prefix. `ctrl+1`..`9` switch workspaces, `ctrl+shift+j`/`k` the next and previous
session, `ctrl+shift+p` goes to an agent, session or pane, `ctrl+shift+h` shows the sidebar. `ctrl+t i` opens the
agents and the Inbox, `ctrl+t g` lazygit, `ctrl+t s` the scratch terminal. `ctrl+t n`/`w`/`W` open a window, close it
and close the session, `ctrl+t h`/`j`/`k`/`l` move focus, `ctrl+t space` is the workspace prefix and `ctrl+t q`
detaches, `ctrl+t ctrl+t` sends `ctrl+t` to the pane. Without the prefix, `ctrl+tab`/`ctrl+shift+tab` cycle windows,
`ctrl+shift+arrows` move focus and `ctrl+shift+1`..`9` move the pane to a workspace. tuios is ctrl only: alt belongs to
aerospace.

### Two Macs

The host entries `mini` (MacMiniM1) and `macbook` (MacBookM2Pro) are in `.config/tuios/config.toml`. After a pull,
run `tuios config apply` once per machine, in a terminal outside tuios.

`dev` ensures the other Mac's nix-darwin and home-infrastructure sessions exist, but only when ssh answers within
3 seconds. When it does not, `dev` prints one line and carries on. `TUIOS_DEV_NO_PEER=1` turns the peer step off.

The sessions run on their own Mac. You only see and attach them from this one. The `*_ssh` commands (`mmdev_ssh`,
`himmdev_ssh`, `nxmmdev_ssh`) are the old ssh-window versions.

On `darwin-rebuild switch`, idle tuios panes are refreshed with the new dotfiles and env vars. When brew upgraded tuios under a running daemon, activation says so: run `tuios restart-server` when the panes can stop (it restarts every program in every pane). Activation also installs tuios agent integrations for every agent on PATH (`tuiosAgentSetup` in `nix-modules/macos/packages-tui.nix`).

Details: [.config/aistack-tuios/README.md](.config/aistack-tuios/README.md)

## 🤖 AI-Powered Git Workflow

This repository includes powerful shell functions for AI-assisted development.

### AI Stack

Each role has one fixed tool; there is no provider picker:

- **gpa / gpc** - llama.cpp (local llama-server on 127.0.0.1:8080) through aider; gpr uses no AI
- **ainfo** - the local llama.cpp model in pi
- **aidev** - on tuios: Claude Code as backbone that plans and reviews, Lumo in a pane for web lookups, a builder that edits (the on-device Qwen3-Coder-30B where present, else a free OpenCode Zen model), talking by tuios mail
- **Review and approval** - Claude Code with Sonnet/Opus (gpa `--tier=<model>` and critical-finding escalation)

### Key Git Functions

#### `gpa` - Git Partial Add with AI Review

Interactive staging with comprehensive checks:

1. **Secrets detection** - Scans for API keys, passwords, tokens
2. **Linting** - the repo's formatter (oxfmt or prettier), nixfmt, ruff, shellcheck (errors only) for sh/bash and `zsh -n` for zsh
3. **Batched AI review** - Reviews code in ~300 line batches
4. **Interactive fixes** - open nvim and aidev on a free workspace of the current tuios session

```bash
gpa                   # Select files, lint, and get AI code review
```

#### `gpc` - Git Push with Commit (AI-generated message)

Automatically generates conventional commit messages:

```bash
gpc                   # AI generates commit message and pushes
gpc -m "subject" -d "body"  # Commit with your message and push
```

#### `gpr` - Git Pull Request

Opens a new branch, a worktree and a draft PR. In tuios it points the session's nvim and zsh windows at the new worktree. `gpr` is an alias for `gpr_func`.

```bash
gpr                   # Interactive: pick feat or fix and a branch name (no AI call)
```

#### Calling `gpr` / `gpa` / `gpc` from AI agents (aidev, Claude Code, opencode, pi)

The caller writes the text; the helpers do the git and GitHub work and never prompt. No flags means the interactive
behavior above, unchanged.

```bash
# new branch + worktree + draft PR, with your title and description (stdout is ONE line of JSON, the log is on stderr)
gpr --auto feat <branch> --title "feat: Add a --shout flag" --description "## Summary\n..."   # or --body-file F
#   -> {"ok":true,"branch":"...","worktree":"...","pr_url":"...","pr_number":123,"title":"..."}
#   -> {"ok":false,"error":"..."}  with a non-zero exit, e.g. for a missing type/branch (it never asks)

# stage everything, secrets scan + linters + AI review, commit with YOUR message, push
gpa --auto -m "Add the --shout flag" -d "Upper-cases the greeting when --shout is given." --json
gpa --auto -m "..." --no-review --json      # the caller already reviewed: secrets scan and linters still run
#   -> {"ok":true,"exit_code":0,"commit":"<sha>","subject":"...","branch":"...","pushed":true,"output_tail":"..."}
#   -> on findings: ok false, a non-zero exit and the findings in output_tail; fix them and run it again

gpc -m "subject" -d "body"                  # commit what is staged with your message and push (no AI call)
```

`-m`/`-d` make the commit subject and body yours (`gpa` hands them to `gpc` through `AI_COMMIT_MESSAGE` /
`AI_COMMIT_BODY`); without `-m` the local model still writes the message. `gpa -m ... --no-review` needs no AI provider
at all. `gpr` still never enters the worktree; use the returned `worktree` path. aidev uses this: when you confirm a
plan it opens the draft PR with the plan's `title` (as `feat: <title>`, at most 72 characters) and a body built from
the plan (summary, each task with its acceptance criteria and verify command, the tiers).
Tests: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_git_auto.py`.

#### gpa review guardrails (which AI findings may block a commit)

The local review model is small: it used to block commits with invented text, findings on untouched code, style
opinions marked Critical, and a different set on every run. `.config/aistack/gpa_review_guard.py` now decides, without
a model, what may block. A finding blocks only when all of this holds:

1. **Evidence**: it quotes an added line of the staged diff of the file it names. Otherwise it is dropped.
2. **Category**: it is Critical and one of `secret-exposure`, `injection`, `destructive-command`, `broken-syntax`,
   `auth-bypass`. Everything else, including every Warning, is advisory: printed, never blocking.
3. **Not already reviewed**: after a fix, only lines that are new since the last round can raise a blocking finding.
   Findings that blocked last round are carried until their line is gone (state in `<git dir>/gpa_review_state.json`,
   reset by a commit).
4. **Confirmed**: the model looks at the finding once more, alone with the code around its line, and may reject it.
   No verdict keeps it blocking.

Dropped and advisory findings are always printed. Review, judge and secrets calls run at temperature 0 with a fixed
seed. The secrets scan and the linters still block as before; `shellcheck` (errors only) now checks sh/bash scripts
and `zsh -n` checks zsh ones. `--no-review` stays off limits for agents.

A person can let one confirmed finding through, on the record:
`gpa --waive <fingerprint> --reason "<why>" -m "<subject>"` adds a `Review-waived:` line to the commit message.
It is refused together with `--auto`. Tests: `python3 .config/aistack/tests/test_review_guard.py`.

#### `aidev` - Claude Code with free builders on tuios

| Command                       | What it does                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------- |
| `aidev [task]`                | Claude, Lumo and a builder in the current tuios session (else session `aidev-<repo>`) |
| `aidev --resume`              | reopen the Claude and Lumo panes of an unfinished run after a daemon restart          |
| `aidev -p "<change>" [files]` | one edit by a free builder in a pane, blocking; `AIDEV_TEST_CMD` must pass            |
| `aidev --handoff <dir>`       | a run for a plan another session wrote (`/aidev-handoff`); one JSON line, no attach   |
| `aidev --rfc <name> [words]`  | a run whose Claude plans from an RFC in `~/.ai/rfcs`                                  |
| `aidev --direct [words]`      | a free builder, interactive, in this terminal (gpa's fix windows use it)              |
| `aidev_status`                | the latest run's work dir, builder and tasks                                          |

The panes talk by tuios mail (session commands: [Terminal: tuios](#terminal-tuios)):

- `plan`: Claude Code is the backbone. You describe the work; it reads the code, writes `plan/prd.json` and
  `plan/verify.json`, builds only when you approve, sends each task to the builder, runs the task's verify commands
  itself and reviews the whole diff.
- `research`: Lumo (pi on lumo-tamer, no tools) for web lookups: current docs, API changes, known bugs.
- `build-local`, `build-free`, `build-billed`: the builder edits the code in three tiers: the on-device
  Qwen3-Coder-30B, a free OpenCode Zen model, billed Claude Code. A task escalates from `build-local` to `build-free`
  to `build-billed`; the billed step asks you first.

Plan, tasks, check output and events are files under `~/.ai/aidev_tuios/<project>-<hash>/` (`plan/`, `runs/<id>/`).
The changes stay uncommitted in the work dir; you commit with `gpa`. Details:
[.config/aistack-tuios/README.md](.config/aistack-tuios/README.md).
Tests: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_aidev_tuios.py` (tests dir
`.config/aistack-tuios/tests`).

### Required Packages

All automatically installed via nix-darwin/package managers:

- `jq` - JSON parsing
- `nixfmt` - Nix formatter
- `prettier` - Multi-language formatter
- `ruff` - Python linter
- `opencode` - AI code assistant
- `llama-cpp` - Local LLM inference (llama-server)
- `gh` - GitHub CLI
- `tuios` - Terminal multiplexer (daily stack)
- `neovim` - Text editor

## 🤖 Claude Code & MCP Integration

`config.nix` automatically sets up Claude Code on activation:

- **Skills**: links each skill (a directory with `SKILL.md`) from `~/model-skills-fullhavoc` and `~/model-skills-perfectserve` into `~/.claude/skills`, and removes stale skill links
- **Settings symlink**: `~/.claude/settings.local.json` → `~/nix-darwin/.claude/settings.local.json`
- **MCP server auto-registration**: reads `~/.config/mcp/claude-desktop-mcp.json` and registers all servers via `claude mcp add`
- **Custom MCP servers**: any `~/mcp-*/` directory with a `package.json` is auto-built and registered
- **tuios agent integrations**: state hooks for every installed agent harness, plus the read-only `tuios mcp` server for Claude Code, installed on activation (`packages-tui.nix`)

### MCP Servers (`.config/mcp/claude-desktop-mcp.json`)

| Server                | Description                                                                                          |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| `mcp-stack-fullhavoc` | Custom local MCP server (`~/mcp-stack-fullhavoc`): infrastructure context, command policy, verbosity |
| `terraform`           | `terraform-mcp-server`: Terraform registry docs                                                      |
| `context7`            | `@upstash/context7-mcp`: up-to-date library documentation                                            |
| `lumo`                | Lumo web search (`~/.config/lumo/lumo_mcp.py`)                                                       |
| `local-edit`          | On-device coder model for multi-file edits (`~/.config/aistack/local_edit_mcp.py`)                   |
| `oczen`               | OpenCode Zen edits, personal hosts (`~/.config/aistack/oczen_mcp.py`)                                |
| `hetzner`             | `@lazyants/hetzner-mcp-server`: Hetzner Cloud, personal hosts                                        |
| `opnsense`            | `@richard-stovall/opnsense-mcp-server`: OPNsense firewall, personal hosts                            |
| `truenas`             | `truenas-mcp-server`: TrueNAS, personal hosts                                                        |
| `awx`                 | `awx-mcp-server`: AWX jobs, personal hosts                                                           |
| `doppler`             | `@dopplerhq/mcp-server`: Doppler secrets, personal hosts                                             |

### Neovim Claude Code Plugin

`claudecode.nvim` (`coder/claudecode.nvim`) is installed via LazyVim with vertical diff layout.

---

## 🛠️ Development Tools

### Editors & IDEs

- **Neovim** - Primary editor (LazyVim configuration, with `claudecode.nvim`)
- **Neovide** - GPU-accelerated Neovim GUI
- **Sublime Text** - GUI text editor
- **GoLand** - JetBrains Go IDE (macOS)

### Terminals

- **Ghostty** - Fast, native GPU-accelerated terminal
- **tuios** - Terminal multiplexer (daily stack)

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

## ✅ CI

`.github/workflows/validate.yml` runs on pushes and pull requests to `main`, with three jobs:

- **Evaluate darwin configurations** (macOS): `nix eval` of `system.drvPath` for `macos_laptop`, `macos_desktop` and `macos_work`
- **ShellCheck** (Ubuntu): `shellcheck --severity=error scripts/*.sh`
- **Secret scan** (Ubuntu): gitleaks over only the commits the push or pull request adds (`gitleaks detect --redact --log-opts=<range>`)

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
- **[aidev on tuios](.config/aistack-tuios/README.md)** - Claude Code planner with free builders in tuios panes

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
**Last Updated:** October 27, 2026
