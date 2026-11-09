    # $HOME/.config is stow's single top-level symlink for the whole .config
    # tree (folded, since until now no leaf under .config needed independent
    # treatment). That means $HOME/.config/opencode/opencode.json resolves
    # straight through to the git-tracked file in the repo -- so an ignore
    # entry for opencode.json in .stow-local-ignore, and an rm+cp of that same
    # resolved path, were both no-ops: stow never re-evaluates an existing
    # correct-looking symlink on restow, and rm+cp of a path that resolves
    # into the repo just recreates the same file in the same place.
    #
    # Unfold $HOME/.config into real-directory + per-item symlinks once
    # (idempotent: a no-op on every run after the first, since stow only
    # folds a target that doesn't exist yet as a real directory) so
    # opencode.json can be deployed independently below instead of dirtying
    # the repo on every activation. Functionally identical for every other
    # stowed item under .config -- each still resolves to the same repo file,
    # just via its own symlink instead of one shared parent symlink.
    #
    # Both $HOME/.config AND $HOME/.config/opencode must be unfolded to real
    # directories in the SAME pass, before stow runs: unfolding just the
    # parent still leaves stow free to fold .config/opencode itself into one
    # symlink (verified empirically -- stow's ignore list affects per-item
    # linking, not the fold decision, at any level it hasn't been forced to
    # unfold yet), which reproduces the exact same problem one level deeper.
    NEEDS_RESTOW=false
    if [ -L "$HOME/.config" ]; then
      rm "$HOME/.config"
      NEEDS_RESTOW=true
    fi
    # mkdir runs unconditionally, NOT gated behind the -L check above: once
    # $HOME/.config's symlink is removed, $HOME/.config/opencode stops
    # existing at all (it only existed via the parent symlink), so an -L
    # check on it here would find neither a symlink nor a real dir and
    # silently skip -- leaving stow to fold it back into one symlink on
    # restow below and reproducing the exact bug this block exists to fix.
    mkdir -p "$HOME/.config"
    if [ -L "$HOME/.config/opencode" ]; then
      rm "$HOME/.config/opencode"
      NEEDS_RESTOW=true
    fi
    mkdir -p "$HOME/.config/opencode"
    if [ "$NEEDS_RESTOW" = true ]; then
      echo "Unfolding \$HOME/.config into per-item symlinks (one-time, needed for independent OpenCode config deployment)..."
      (cd "$HOME/nix-darwin" && @stow@/bin/stow -R .) || echo "Warning: failed to re-stow after unfolding \$HOME/.config"
    fi

