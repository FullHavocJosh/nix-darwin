{ pkgs, ... }:
{
  nixpkgs.config.allowUnfree = true;
  nixpkgs.hostPlatform = "aarch64-darwin";
  nix.settings.experimental-features = "nix-command flakes";
  programs.zsh.enable = true;
  system.stateVersion = 5;

  system.activationScripts.postUserActivation.text = ''
    # Symlink global gitignore from nix-darwin to home directory
    if [ ! -L "$HOME/.gitignore_global" ] || [ "$(readlink "$HOME/.gitignore_global")" != "$HOME/nix-darwin/.gitignore_global" ]; then
      echo "Creating symlink for global gitignore..."
      ln -sf "$HOME/nix-darwin/.gitignore_global" "$HOME/.gitignore_global"
    fi

    # Configure git to use global gitignore
    if command -v git &>/dev/null; then
      CURRENT_EXCLUDES=$(git config --global core.excludesfile 2>/dev/null || echo "")
      if [ "$CURRENT_EXCLUDES" != "$HOME/.gitignore_global" ]; then
        echo "Configuring git to use global gitignore..."
        git config --global core.excludesfile "$HOME/.gitignore_global"
      fi
    fi

    # Install GitHub Copilot CLI extension if not already installed
    if command -v gh &>/dev/null; then
      if ! gh extension list 2>/dev/null | grep -q "gh-copilot"; then
        echo "Installing GitHub Copilot CLI extension..."
        gh extension install github/gh-copilot 2>/dev/null || echo "Failed to install gh-copilot extension"
      fi
    fi

    HOMEBREW_PREFIX="/opt/homebrew"

    # Add Homebrew bin to PATH for this script
    export PATH="$HOMEBREW_PREFIX/bin:$PATH"

    if command -v npm &>/dev/null && command -v node &>/dev/null; then
      MCP_FOUND=0
      for MCP_DIR in "$HOME"/mcp-*/; do
        [ -d "$MCP_DIR" ] || continue
        [ -f "$MCP_DIR/package.json" ] || continue
        MCP_FOUND=1
        MCP_NAME=$(basename "$MCP_DIR")
        MCP_DIST="$MCP_DIR/dist/index.js"
        echo "Checking MCP server: $MCP_NAME"
        cd "$MCP_DIR"
        if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ] || [ "package-lock.json" -nt "node_modules" ]; then
          echo "Installing dependencies for $MCP_NAME..."
          npm install || echo "Failed to install dependencies for $MCP_NAME"
        fi
        if [ ! -f "$MCP_DIST" ] || [ "src" -nt "$MCP_DIST" ] || [ "package-lock.json" -nt "$MCP_DIST" ]; then
          echo "Building $MCP_NAME..."
          npm run build && echo "$MCP_NAME built successfully!" || echo "Failed to build $MCP_NAME"
        else
          echo "$MCP_NAME is up to date."
        fi
        if [ -f "$MCP_DIST" ] && command -v claude &>/dev/null; then
          claude mcp add --scope user "$MCP_NAME" node "$MCP_DIST" 2>/dev/null || true
        fi
      done
      [ "$MCP_FOUND" -eq 0 ] && echo "No ~/mcp-* servers found, skipping."
    else
      echo "Skipping MCP server builds (npm or node not available in PATH)"
    fi

    echo "Creating font aliases for terminal compatibility..."

    ALIAS_FONT_DIR="$HOME/Library/Fonts/Aliased"

    ${pkgs.coreutils}/bin/rm -rf "$ALIAS_FONT_DIR"
    mkdir -p "$ALIAS_FONT_DIR"

    create_font_alias() {
      local source_font="$1"
      local new_family_name="$2"
      local output_font="$3"

      if [ -f "$source_font" ]; then
        echo "Creating alias: $(basename "$output_font")"

        local temp_dir
        local temp_xml
        local temp_font_base

        temp_dir=$(${pkgs.coreutils}/bin/mktemp -d)
        temp_xml="$temp_dir/font.ttx"
        temp_font_base="$temp_dir/font"

        ${pkgs.python3Packages.fonttools}/bin/ttx -t name -o "$temp_xml" "$source_font" 2>/dev/null || return 1

        ${pkgs.gnused}/bin/sed -i \
          -e "s|JetBrainsMono NFM|$new_family_name|g" \
          -e "s|JetBrainsMono Nerd Font Mono|$new_family_name|g" \
          "$temp_xml" 2>/dev/null || return 1

        ${pkgs.coreutils}/bin/cp "$source_font" "$temp_font_base.ttf"

        # ttx creates font#1.ttf when font.ttf already exists
        ${pkgs.python3Packages.fonttools}/bin/ttx -m "$temp_font_base.ttf" "$temp_xml" 2>/dev/null || return 1

        if [ -f "$temp_font_base#1.ttf" ]; then
          ${pkgs.coreutils}/bin/mv "$temp_font_base#1.ttf" "$output_font"
        else
          ${pkgs.coreutils}/bin/mv "$temp_font_base.ttf" "$output_font"
        fi

        ${pkgs.coreutils}/bin/rm -rf "$temp_dir"
      fi
    }

    for style in Regular Bold Italic BoldItalic; do
      source="$HOME/Library/Fonts/JetBrainsMonoNerdFontMono-$style.ttf"
      target="$ALIAS_FONT_DIR/JetBrainsMono-$style.ttf"

      if [ -f "$source" ]; then
        create_font_alias "$source" "JetBrains Mono" "$target"
      fi
    done

    echo "Font aliases created. Rebuilding font cache..."

    ${pkgs.coreutils}/bin/touch "$HOME/Library/Fonts/Aliased"
    /System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/atsutil databases -remove 2>/dev/null || true
    /System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/atsutil server -shutdown 2>/dev/null || true
    /System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/atsutil server -ping 2>/dev/null || true

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

    echo "Managing global npm packages..."
    if command -v npm &>/dev/null; then
      if ! npm list -g jsonlint &>/dev/null; then
        echo "Installing jsonlint..."
        npm install -g jsonlint 2>&1 | grep -v "npm warn" || echo "Failed to install jsonlint"
      fi

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

    NSGlobalDomain._HIHideMenuBar = false;
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
