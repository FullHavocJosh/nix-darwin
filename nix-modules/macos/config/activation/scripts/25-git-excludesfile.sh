    if command -v git &>/dev/null; then
      CURRENT_EXCLUDES=$(git config --global core.excludesfile 2>/dev/null || echo "")
      if [ "$CURRENT_EXCLUDES" != "$HOME/.gitignore_global" ]; then
        echo "Configuring git to use global gitignore..."
        git config --global core.excludesfile "$HOME/.gitignore_global"
      fi
    fi

