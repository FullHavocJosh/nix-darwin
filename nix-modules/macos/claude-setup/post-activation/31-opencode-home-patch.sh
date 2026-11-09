    if [ -f "$HOME/.config/opencode/opencode.json" ]; then
      echo "Patching opencode.json with correct home path..."
      @gnused@/bin/sed -i "s|__HOME__|$HOME|g" "$HOME/.config/opencode/opencode.json"
    fi

