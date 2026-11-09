    echo "Checking for macOS system updates..."
    UPDATES_AVAILABLE=$(softwareupdate --list 2>&1)

    if echo "$UPDATES_AVAILABLE" | grep -q "Software Update found"; then
      echo "════════════════════════════════════════════════════════════════"
      echo "macOS System Updates Available:"
      echo "────────────────────────────────────────────────────────────────"
      echo "$UPDATES_AVAILABLE" | grep -A 100 "Software Update found"
      echo "════════════════════════════════════════════════════════════════"
      echo ""
      echo "To install updates, run one of:"
      echo "  softwareupdate --install --all --verbose              # Install all (with verbose output)"
      echo "  softwareupdate --install --recommended --verbose      # Install recommended only"
      echo "  softwareupdate --install <update-name> --verbose      # Install specific update"
      echo ""
      echo "NOTE: softwareupdate has limited progress indicators. Use --verbose for more output,"
      echo "      but expect periods of no output during large downloads. Monitor with:"
      echo "      watch -n 2 'ls -lh /Library/Updates'  # See download progress in separate terminal"
      echo ""
    elif echo "$UPDATES_AVAILABLE" | grep -q "No new software available"; then
      echo "macOS is up to date - no system updates available"
    else
      echo "Unable to check for macOS updates (may require sudo or network connection)"
    fi

