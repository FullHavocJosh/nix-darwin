# CRUSH.md - nix-darwin Configuration & Dotfiles

## Build/Deploy Commands
- **Deploy personal**: `darwin-rebuild switch --flake ~/nix-darwin#macos_personal`
- **Deploy work**: `darwin-rebuild switch --flake ~/nix-darwin#macos_work`
- **Update packages**: `nix flake update && darwin-rebuild switch --flake ~/nix-darwin#macos_personal`
- **Deploy dotfiles**: `stow . -t ~`
- **Format Nix**: `nixfmt *.nix nix-modules/**/*.nix`
- **Lint**: `ansible-lint` (for Ansible playbooks)

## Ansible Commands (Fedora Linux)
- **Deploy personal**: `cd ansible-fedora && ansible-playbook -i inventory/fedora playbooks/fedora-personal.yml --ask-become-pass`
- **Deploy work**: `cd ansible-fedora && ansible-playbook -i inventory/fedora playbooks/fedora-work.yml --ask-become-pass`
- **Deploy base only**: `cd ansible-fedora && ansible-playbook -i inventory/fedora playbooks/fedora-base.yml --ask-become-pass`
- **Specific tags**: `cd ansible-fedora && ansible-playbook -i inventory/fedora playbooks/fedora-personal.yml --tags packages --ask-become-pass`
- **Lint playbooks**: `cd ansible-fedora && ansible-lint playbooks/`

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