# dotfiles

This directory contains the dotfiles for my systems

## Requirements

Ensure you have the following installed on your system

### For MacOS
#### Settings:
```
System Preferences -> Privacy -> Full Disk Access -> Terminal
```
#### Terminal Commands:
```
brew install git stow
${tty_bold}softwareupdate --install-rosetta${tty_reset}
```

### For Fedora

```
yum install git stow
```

## Installation

First, check out the dotfiles repo in your $HOME directory using git

```
$ git clone git@github.com:FullHavocJosh/dotfiles.git
$ cd dotfiles
$ stow .
```

# Install Nix Package Manager:
sh <(curl -L https://nixos.org/nix/install)

# Execute Nix Config:
nix run nix-darwin --extra-experimental-features "nix-command flakes" --switch --flake ~/.config/nix#macos

# Check if Darwin Tools are Installed:
which darwin-rebuild

# Deploy Darwin Config
darwin-rebuild switch --flake ~/.config/nix#macos

# Find Nix Packages * = name of package/app
nix search nixpkgs *
# or search.nixos.org

# Updating Apps
nix flake update
darwin-rebuild switch --flake ~/.config/nix#macos
