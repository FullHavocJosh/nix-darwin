    # tuios on macOS reads Application Support unless XDG_CONFIG_HOME is set, so a daemon restarted from a plain
    # shell (tuios restart-server) would load a generated default: permissions mode open, grants admin only, no
    # respond for aidev. Point that path at the stowed config; a generated file is kept as config.toml.bak.
    tuios_support="$HOME/Library/Application Support/tuios"
    mkdir -p "$tuios_support"
    if [ -f "$tuios_support/config.toml" ] && [ ! -L "$tuios_support/config.toml" ]; then
      mv "$tuios_support/config.toml" "$tuios_support/config.toml.bak"
    fi
    ln -sfn "$HOME/.config/tuios/config.toml" "$tuios_support/config.toml"

