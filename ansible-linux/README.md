# Fedora Linux Configuration with Ansible

This directory contains Ansible playbooks that mirror the functionality of the nix-darwin configuration for Fedora Linux systems.

## Structure

- `playbooks/` - Main playbooks for different use cases
- `roles/` - Modular roles that can be mixed and matched
- `inventory/` - Inventory files for different environments

## Playbooks

### Base System
- `fedora-base.yml` - Core system configuration and packages

### Specific Configurations
- `fedora-personal.yml` - Personal desktop setup with gaming and media apps
- `fedora-work.yml` - Work environment with professional tools

## Roles

- `fedora-packages` - Core CLI tools, development tools, language servers
- `system-config` - System settings, repositories, shell configuration
- `gui-applications` - Desktop applications via Flatpak and DNF
- `personal-config` - Gaming, media, and personal applications
- `work-config` - Kubernetes tools, work-specific applications

## Usage

### Run Complete Personal Setup
```bash
cd ansible-fedora
ansible-playbook -i inventory/fedora playbooks/fedora-personal.yml --ask-become-pass
```

### Run Complete Work Setup
```bash
cd ansible-fedora
ansible-playbook -i inventory/fedora playbooks/fedora-work.yml --ask-become-pass
```

### Run Specific Components
```bash
# Only install packages
ansible-playbook -i inventory/fedora playbooks/fedora-base.yml --tags packages --ask-become-pass

# Only configure GUI applications
ansible-playbook -i inventory/fedora playbooks/fedora-base.yml --tags gui --ask-become-pass
```

## Notes

- Run with `--ask-become-pass` to provide sudo password for system-level changes
- Flatpak applications are installed per-user (no sudo required)
- DNF packages require sudo privileges
- Some manual configuration may be needed for dotfiles - create `~/fedora-dotfiles` and use `stow . -t ~`

## Equivalent nix-darwin Configurations

- `fedora-personal.yml` ≈ `macos_personal` nix-darwin configuration
- `fedora-work.yml` ≈ `macos_work` nix-darwin configuration
- `fedora-packages` role ≈ `packages.nix` homebrew formulas and brews
- `gui-applications` role ≈ `packages.nix` homebrew casks
- `system-config` role ≈ `config.nix` system defaults