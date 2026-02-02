{ pkgs, ... }:
{
  nixpkgs.config.allowUnfree = true;
  nixpkgs.hostPlatform = "aarch64-darwin";
  nix.settings.experimental-features = "nix-command flakes";
  programs.zsh.enable = true;
  system.stateVersion = 5;

  # Create font aliases by modifying font metadata
  # This allows Core Text to recognize "JetBrains Mono" as an alias for "JetBrainsMono Nerd Font Mono"
  system.activationScripts.postUserActivation.text = ''
    # Install GitHub Copilot CLI extension if not already installed
    if command -v gh &>/dev/null; then
      if ! gh extension list 2>/dev/null | grep -q "gh-copilot"; then
        echo "Installing GitHub Copilot CLI extension..."
        gh extension install github/gh-copilot 2>/dev/null || echo "Failed to install gh-copilot extension"
      fi
    fi

    # Build and install ferrosonic if not already installed or if source has changed
    FERROSONIC_DIR="$HOME/ferrosonic"
    FERROSONIC_BIN="/usr/local/bin/ferrosonic"
    HOMEBREW_PREFIX="/opt/homebrew"

    # Add Homebrew bin to PATH for this script
    export PATH="$HOMEBREW_PREFIX/bin:$PATH"

    if command -v cargo &>/dev/null && command -v git &>/dev/null && command -v rustc &>/dev/null; then
      echo "Checking ferrosonic installation..."

      # Clone or update repository
      if [ ! -d "$FERROSONIC_DIR" ]; then
        echo "Cloning ferrosonic repository..."
        git clone https://github.com/jaidaken/ferrosonic.git "$FERROSONIC_DIR" || echo "Failed to clone ferrosonic"
      else
        echo "Updating ferrosonic repository..."
        cd "$FERROSONIC_DIR" && git pull || echo "Failed to update ferrosonic"
      fi

      # Build and install if directory exists
      if [ -d "$FERROSONIC_DIR" ]; then
        cd "$FERROSONIC_DIR"

        # Check if we need to rebuild (source changed or binary doesn't exist)
        if [ ! -f "$FERROSONIC_BIN" ] || [ "$FERROSONIC_DIR/src" -nt "$FERROSONIC_BIN" ]; then
          echo "Building ferrosonic (this may take a few minutes)..."
          cargo build --release && \
          echo "Installing ferrosonic to /usr/local/bin..." && \
          sudo cp target/release/ferrosonic "$FERROSONIC_BIN" && \
          echo "Ferrosonic installed successfully!" || \
          echo "Failed to build/install ferrosonic. You can manually run: cd ~/ferrosonic && cargo build --release && sudo cp target/release/ferrosonic /usr/local/bin/"
        else
          echo "Ferrosonic is already up to date."
        fi
      fi
    else
      echo "Skipping ferrosonic installation (cargo, rustc, or git not available in PATH)"
    fi

    echo "Creating font aliases for terminal compatibility..."

    # Create aliased fonts directory
    ALIAS_FONT_DIR="$HOME/Library/Fonts/Aliased"

    # Clean old fonts to force regeneration
    ${pkgs.coreutils}/bin/rm -rf "$ALIAS_FONT_DIR"
    mkdir -p "$ALIAS_FONT_DIR"

    # Function to create font alias
    create_font_alias() {
      local source_font="$1"
      local new_family_name="$2"
      local output_font="$3"

      if [ -f "$source_font" ]; then
        echo "Creating alias: $(basename "$output_font")"

        # Use fonttools to modify font name table
        local temp_dir
        local temp_xml
        local temp_font_base

        temp_dir=$(${pkgs.coreutils}/bin/mktemp -d)
        temp_xml="$temp_dir/font.ttx"
        temp_font_base="$temp_dir/font"

        # Extract name table from source font
        ${pkgs.python3Packages.fonttools}/bin/ttx -t name -o "$temp_xml" "$source_font" 2>/dev/null || return 1

        # Modify family name in the XML
        # nameID 1 = Font Family, nameID 4 = Full Name, nameID 16 = Typographic Family
        ${pkgs.gnused}/bin/sed -i \
          -e "s|JetBrainsMono NFM|$new_family_name|g" \
          -e "s|JetBrainsMono Nerd Font Mono|$new_family_name|g" \
          "$temp_xml" 2>/dev/null || return 1

        # Copy source font to temp location
        ${pkgs.coreutils}/bin/cp "$source_font" "$temp_font_base.ttf"

        # Merge modified name table - this creates font#1.ttf (won't overwrite existing)
        ${pkgs.python3Packages.fonttools}/bin/ttx -m "$temp_font_base.ttf" "$temp_xml" 2>/dev/null || return 1

        # Move the newly created modified font to output location
        # ttx creates font#1.ttf when font.ttf already exists
        if [ -f "$temp_font_base#1.ttf" ]; then
          ${pkgs.coreutils}/bin/mv "$temp_font_base#1.ttf" "$output_font"
        else
          ${pkgs.coreutils}/bin/mv "$temp_font_base.ttf" "$output_font"
        fi

        # Clean up
        ${pkgs.coreutils}/bin/rm -rf "$temp_dir"
      fi
    }

    # Create aliases for Regular, Bold, Italic, BoldItalic
    for style in Regular Bold Italic BoldItalic; do
      source="$HOME/Library/Fonts/JetBrainsMonoNerdFontMono-$style.ttf"
      target="$ALIAS_FONT_DIR/JetBrainsMono-$style.ttf"

      if [ -f "$source" ]; then
        create_font_alias "$source" "JetBrains Mono" "$target"
      fi
    done

    echo "Font aliases created. Rebuilding font cache..."

    # Force macOS to rebuild font cache
    ${pkgs.coreutils}/bin/touch "$HOME/Library/Fonts/Aliased"
    /System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/atsutil databases -remove 2>/dev/null || true
    /System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/atsutil server -shutdown 2>/dev/null || true
    /System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/atsutil server -ping 2>/dev/null || true

    echo "Managing global npm packages..."
    # Check if npm is available
    if command -v npm &>/dev/null; then
      # Install opencode-ai if not already installed
      if ! npm list -g opencode-ai &>/dev/null; then
        echo "Installing opencode-ai..."
        npm install -g opencode-ai 2>&1 | grep -v "npm warn" || echo "Failed to install opencode-ai"
      fi

      # Get list of globally installed packages that need updates
      OUTDATED=$(npm outdated -g --json 2>/dev/null || echo "{}")
      if [ -n "$OUTDATED" ] && [ "$OUTDATED" != "{}" ]; then
        OUTDATED_COUNT=$(echo "$OUTDATED" | jq 'length' 2>/dev/null || echo "0")

        if [ "$OUTDATED_COUNT" -gt 0 ] 2>/dev/null; then
          echo "Found $OUTDATED_COUNT outdated global npm package(s)"
          echo "$OUTDATED" | jq -r 'keys[]' 2>/dev/null | while read -r pkg; do
            CURRENT=$(echo "$OUTDATED" | jq -r ".[\"$pkg\"].current" 2>/dev/null)
            LATEST=$(echo "$OUTDATED" | jq -r ".[\"$pkg\"].latest" 2>/dev/null)
            echo "  Updating $pkg: $CURRENT → $LATEST"
          done

          # Update all global packages
          npm update -g 2>&1 | grep -v "npm warn" || true
          echo "Finished updating global npm packages"
        else
          echo "All global npm packages are up to date"
        fi
      else
        echo "All global npm packages are up to date"
      fi
    else
      echo "npm not found, skipping npm package management"
    fi
  '';

  system.defaults = {
    NSGlobalDomain.AppleInterfaceStyle = "Dark";
    NSGlobalDomain.NSScrollAnimationEnabled = true;
    NSGlobalDomain.NSWindowResizeTime = 0.05;

    dock.autohide = true;
    dock.autohide-delay = 0.05;
    dock.autohide-time-modifier = 0.05;
    dock.tilesize = 32;
    dock.largesize = 64;
    dock.magnification = true;
    dock.mineffect = "genie";
    dock.mru-spaces = false;
    dock.showhidden = true;
    dock.launchanim = true;
    dock.orientation = "bottom";
    dock.static-only = false;
    dock.show-recents = false;
    dock.slow-motion-allowed = false;
    dock.dashboard-in-overlay = true;
    dock.expose-group-apps = false;
    dock.expose-animation-duration = 0.05;
    dock.minimize-to-application = false;
    dock.wvous-bl-corner = 1;
    dock.wvous-br-corner = 1;
    dock.wvous-tl-corner = 1;
    dock.wvous-tr-corner = 1;

    NSGlobalDomain._HIHideMenuBar = true;
    menuExtraClock.IsAnalog = false;
    menuExtraClock.ShowAMPM = false;
    menuExtraClock.ShowDate = 0;
    menuExtraClock.Show24Hour = false;
    menuExtraClock.ShowSeconds = false;
    menuExtraClock.ShowDayOfWeek = false;

    finder.ShowPathbar = true;
    finder.ShowStatusBar = true;
    finder.AppleShowAllFiles = true;
    finder.AppleShowAllExtensions = true;
    finder.FXPreferredViewStyle = "clmv";
    finder.FXDefaultSearchScope = "SCcf";
    finder.FXEnableExtensionChangeWarning = false;
    finder._FXSortFoldersFirst = true;
    finder._FXShowPosixPathInTitle = true;
    finder.QuitMenuItem = false;
    finder.CreateDesktop = false;
    NSGlobalDomain.AppleShowAllFiles = true;
    NSGlobalDomain.AppleShowAllExtensions = true;

    loginwindow.GuestEnabled = false;

    trackpad.TrackpadThreeFingerDrag = false;
    trackpad.Dragging = false;
    NSGlobalDomain.AppleEnableSwipeNavigateWithScrolls = false;
    NSGlobalDomain.NSWindowShouldDragOnGesture = false;

    NSGlobalDomain."com.apple.keyboard.fnState" = true;
    NSGlobalDomain.KeyRepeat = 2;
    NSGlobalDomain.InitialKeyRepeat = 15;

    WindowManager.AutoHide = true;
    WindowManager.StandardHideDesktopIcons = true;
    WindowManager.HideDesktop = true;
    WindowManager.EnableStandardClickToShowDesktop = false;
    WindowManager.GloballyEnabled = false;
    WindowManager.AppWindowGroupingBehavior = false;

    universalaccess.mouseDriverCursorSize = 1.25;

    NSGlobalDomain.ApplePressAndHoldEnabled = false;
    NSGlobalDomain.NSDocumentSaveNewDocumentsToCloud = true;
    NSGlobalDomain.NSAutomaticInlinePredictionEnabled = false;
    NSGlobalDomain.NSAutomaticSpellingCorrectionEnabled = false;
    NSGlobalDomain.NSAutomaticPeriodSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticCapitalizationEnabled = false;
    NSGlobalDomain.NSAutomaticDashSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticQuoteSubstitutionEnabled = false;
    NSGlobalDomain.AppleScrollerPagingBehavior = true;
  };
}
