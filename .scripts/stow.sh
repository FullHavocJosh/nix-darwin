#!/usr/bin/env bash
echo "Stowing dotfiles..."
cd /home/havoc/nix-darwin || { echo "Failed to cd into ~/nix-darwin/dotfiles"; exit 1; }
echo "Stowing $dir..."
stow -R . || { echo "Failed to stow ."; exit 1; }
