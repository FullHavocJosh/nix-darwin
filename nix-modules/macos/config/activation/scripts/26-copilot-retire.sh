    # GitHub Copilot is retired from this setup: remove the gh-copilot extension older activations installed.
    if command -v gh &>/dev/null && gh extension list 2>/dev/null | grep -q "gh-copilot"; then
      echo "Removing retired GitHub Copilot CLI extension..."
      gh extension remove gh-copilot 2>/dev/null || echo "Failed to remove gh-copilot extension"
    fi

