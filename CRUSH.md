# CRUSH.md - nix-darwin Configuration & Dotfiles

## Build/Deploy Commands
- **Deploy personal**: `darwin-rebuild switch --flake ~/nix-darwin#macos_personal`
- **Deploy work**: `darwin-rebuild switch --flake ~/nix-darwin#macos_work`
- **Update packages**: `nix flake update && darwin-rebuild switch --flake ~/nix-darwin#macos_personal`
- **Deploy dotfiles**: `stow . -t ~`
- **Format Nix**: `nixfmt *.nix nix-modules/**/*.nix`
- **Lint**: `ansible-lint` (for Ansible playbooks)

## Crush CLI Commands
- **Smart launch**: `crush` - Automatically checks AWS SSO status and only authenticates if needed for Bedrock Claude Sonnet access
- **Manual AWS SSO**: `asl` - Force AWS SSO login
- **Profile switch**: `sso <profile>` - Login and switch to specific AWS profile
- **Profile switch (no login)**: `ssoswitch <profile>` - Switch profile using existing session

## Ansible Commands (Fedora Linux)
- **Deploy personal**: `cd ansible-fedora && ansible-playbook -i inventory/fedora playbooks/fedora-personal.yml --ask-become-pass`
- **Deploy work**: `cd ansible-fedora && ansible-playbook -i inventory/fedora playbooks/fedora-work.yml --ask-become-pass`
- **Deploy base only**: `cd ansible-fedora && ansible-playbook -i inventory/fedora playbooks/fedora-base.yml --ask-become-pass`
- **Specific tags**: `cd ansible-fedora && ansible-playbook -i inventory/fedora playbooks/fedora-personal.yml --tags packages --ask-become-pass`
- **Lint playbooks**: `cd ansible-fedora && ansible-lint playbooks/`

## Troubleshooting

### AWS MCP Transport Errors
If AWS MCP servers fail with "transport error" or "Too many open files":
1. **Root cause**: macOS default file descriptor limit (256) is too low for uvx/Python
2. **Fix applied**: Added `ulimit -n 4096` to `.zshrc_ulimit` (sourced in `.zshrc`)
3. **Test fix**: `exec zsh -c "ulimit -n 4096; uvx awslabs.core-mcp-server@latest --version"`
4. **Permanent**: Restart terminal or run `source ~/.zshrc` to apply

### Neovim Terraform Syntax Highlighting
If `.tf` files don't have syntax highlighting:
1. **Root cause**: Missing `terraform` treesitter parser and filetype detection
2. **Fix applied**: Added `terraform` parser to treesitter config + filetype detection
3. **Restart nvim**: `:TSUpdate terraform` then restart nvim
4. **Verify**: `:set filetype?` in a .tf file should show `filetype=terraform`

## Code Style & Conventions
- **File structure**: Modular approach with separate configs (personal.nix, work.nix, packages.nix)
- **Nix formatting**: Use nixfmt for consistent formatting
- **Shell**: Zsh with modular configuration files (.zshrc_*)
- **Themes**: Catppuccin theme consistently across applications
- **Comments**: Use descriptive section headers with ### for major sections
- **Package management**: Homebrew formulas, casks, and Mac App Store apps in packages.nix
- **Environment variables**: Separate secure/insecure env var files
- **Naming**: Use descriptive names (macos_personal vs macos_work)

## Configuration Files
- **Main config**: flake.nix (defines system configurations)
- **Packages**: nix-modules/macos/packages.nix (Homebrew packages/casks)
- **System config**: nix-modules/macos/config.nix (macOS system settings)
- **Dotfiles**: .config/* (application-specific configurations)
- **Shell**: .zshrc with modular includes (.zshrc_aliases, .zshrc_functions, etc.)

## Key Tools & Languages
- **Nix/Darwin**: Declarative system management
- **Shell**: Zsh, tmux, modern CLI tools (eza, fd, ripgrep)
- **Development**: Go, Python, Rust, Neovim/LazyVim, LSP servers
- **Infrastructure**: Ansible, Terraform, OpenTofu