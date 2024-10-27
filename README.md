# nix-darwin

This repo contains my nix-darwin config and .files, which will be applied via stow when darwin-rebuild switch is run. 

## Requirements

Ensure you have the following installed on your system

### For MacOS
#### Settings:
```
System Preferences -> Privacy -> Full Disk Access -> Terminal
```
#### Terminal Commands:
```
brew install git
${tty_bold}softwareupdate --install-rosetta${tty_reset}
```

### For Fedora

```
yum install git
```

## Installation

First, check out the nix-darwin repo in your $HOME directory using git

```
$ git clone git@github.com:FullHavocJosh/nix-darwin.git
```

## Install Nix Package Manager:
```
sh <(curl -L https://nixos.org/nix/install)
```
## Execute Nix Config:
```
nix run nix-darwin --extra-experimental-features "nix-command flakes" --switch --flake ~/nix-darwin#macos
```
## Check if Darwin Tools are Installed:
```
which darwin-rebuild
```
## Deploy Darwin Config
```
darwin-rebuild switch --flake ~/nix-darwin#macos
```
## Find Nix Packages * = name of package/app
```
nix search nixpkgs *
```
## or search.nixos.org

## Updating Apps
```
nix flake update
darwin-rebuild switch --flake ~/nix-darwin#macos
```
## Notes:
```
nix-build https://github.com/LnL7/nix-darwin/archive/master.tar.gz -A installer
./result/bin/darwin-installer
nix-channel --add https://github.com/LnL7/nix-darwin/archive/master.tar.gz darwin
nix-channel --update
```