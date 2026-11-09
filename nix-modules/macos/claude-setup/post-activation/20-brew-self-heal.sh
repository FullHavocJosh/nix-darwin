    # Self-heal a known Homebrew gap: `brew bundle`'s upgrade (onActivation.upgrade
    # above) only touches formulae explicitly listed in the Brewfile, not their
    # transitive dependencies. When a dependency gets a new dylib SONAME (e.g.
    # simdutf 35 -> 36) but a dependent that isn't itself in the Brewfile (e.g.
    # merve, a node build dependency) doesn't get rebuilt against it, node/npm
    # break with "Library not loaded" -- confirmed hitting this on two separate
    # machines. Detected generically (node itself, not any specific formula)
    # since tomorrow's stale dependent will have a different name.
    if ! node --version >/dev/null 2>&1; then
      echo "node is broken (likely a stale bottled dependency) -- running brew upgrade to self-heal..."
      # </dev/null is load-bearing, not defensive style: this whole block
      # is itself being read by bash as a script fed over stdin (the
      # sudo -u ... bash <<'USERSCRIPT' heredoc above). Without this,
      # `brew upgrade` inherits that same stdin fd, and confirmed live:
      # when it has real work to do (here, 27 outdated packages), some
      # subprocess of brew reads from it and consumes bytes bash hadn't
      # executed yet -- the rest of this heredoc (opencode.json patching,
      # claude-dashboard, claudeTuiSetup, tokenOptimizationSetup, Opcode
      # install) got silently skipped, with the raw unexecuted script text
      # dumped to stdout instead of running.
      brew upgrade </dev/null 2>&1 || true
    fi

