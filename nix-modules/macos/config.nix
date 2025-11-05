{ pkgs, config, lib, ... }: {
  nixpkgs.config.allowUnfree = true;
  nixpkgs.hostPlatform = "aarch64-darwin";
  nix.settings.experimental-features = "nix-command flakes";
  programs.zsh.enable = true;
  system.stateVersion = 5;

  # Create font aliases by modifying font metadata
  # This allows Core Text to recognize "JetBrains Mono" as an alias for "JetBrainsMono Nerd Font Mono"
  system.activationScripts.postUserActivation.text = ''
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
