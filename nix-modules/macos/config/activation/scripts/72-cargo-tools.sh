    if command -v cargo &>/dev/null; then
      if ! command -v nexus &>/dev/null; then
        echo "Installing nexus-tui..."
        # Not on crates.io; pinned to a specific audited commit.
        # Audited at edd908b: Kubernetes TUI, no network/fs side effects beyond kubeconfig reads.
        # To update: review the diff from edd908b to the new commit before changing --rev.
        cargo install --git https://github.com/markx3/nexus-tui --rev edd908b26b4c19d9dd8e5cf3784f60f4b273669d 2>&1 || echo "Failed to install nexus-tui"
      fi
    fi

