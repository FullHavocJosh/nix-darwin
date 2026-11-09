    if [ ! -L "$HOME/.gitignore_global" ] || [ "$(readlink "$HOME/.gitignore_global")" != "$HOME/nix-darwin/.gitignore_global" ]; then
      echo "Creating symlink for global gitignore..."
      ln -sf "$HOME/nix-darwin/.gitignore_global" "$HOME/.gitignore_global"
    fi

