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

    # Deploy and build fullhavoc-context-guardian MCP server
    # 
    # This MCP server provides context about home infrastructure and AI contexts.
    # 
    # Important directories:
    #   - ~/aicontexts: AI context documentation for various systems
    #   - ~/home-infrastructure: Infrastructure as Code (K3s, Ansible, Terraform)
    # 
    # Network Architecture (see ~/aicontexts/NETWORK-ARCHITECTURE.md):
    #   - OPNsense Nginx: SSL/TLS termination + ALL security (HSTS, auth, rate limiting, WAF)
    #   - K8s Nginx Ingress: BASIC LOAD BALANCING ONLY (no SSL, no security, just routing)
    # 
    MCP_TEMPLATE="$HOME/nix-darwin/mcp-servers/fullhavoc-context-guardian"
    MCP_DIR="$HOME/fullhavoc-context-guardian-mcp-server"
    MCP_DIST="$MCP_DIR/dist/index.js"
    MCP_CONTEXT="$MCP_DIR/infrastructure-context.json"

    if command -v npm &>/dev/null && command -v node &>/dev/null; then
      echo "Deploying fullhavoc-context-guardian MCP server..."

      # Create target directory if it doesn't exist
      mkdir -p "$MCP_DIR"

      # Sync template to target (preserve infrastructure-context.json if it exists)
      if [ -f "$MCP_CONTEXT" ]; then
        # Backup existing context
        cp "$MCP_CONTEXT" "$MCP_CONTEXT.backup"
      fi

      # Sync all files from template
      ${pkgs.rsync}/bin/rsync -av --exclude='node_modules' --exclude='dist' --exclude='.git' \
        "$MCP_TEMPLATE/" "$MCP_DIR/"

      # Restore context if we backed it up
      if [ -f "$MCP_CONTEXT.backup" ]; then
        mv "$MCP_CONTEXT.backup" "$MCP_CONTEXT"
      fi

      cd "$MCP_DIR"

      # Check if dependencies are installed or need updating
      if [ ! -d "node_modules" ] || [ "$MCP_TEMPLATE/package.json" -nt "node_modules" ] || [ "$MCP_TEMPLATE/package-lock.json" -nt "node_modules" ]; then
        echo "Installing MCP server dependencies..."
        npm install || echo "Failed to install MCP server dependencies"
      fi

      # Check if we need to rebuild (source changed, lockfile changed, or dist doesn't exist)
      if [ ! -f "$MCP_DIST" ] || [ "$MCP_TEMPLATE/src" -nt "$MCP_DIST" ] || [ "$MCP_TEMPLATE/package-lock.json" -nt "$MCP_DIST" ]; then
        echo "Building fullhavoc-context-guardian MCP server..."
        npm run build && \
        echo "MCP server deployed and built successfully!" || \
        echo "Failed to build MCP server. You can manually run: cd ~/fullhavoc-context-guardian-mcp-server && npm install && npm run build"
      else
        echo "MCP server is already up to date."
      fi
    else
      echo "Skipping MCP server deployment (npm or node not available in PATH)"
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
      # Note: opencode is already provided by Homebrew, no need for opencode-ai npm package

      # Install jsonlint if not already installed
      if ! npm list -g jsonlint &>/dev/null; then
        echo "Installing jsonlint..."
        npm install -g jsonlint 2>&1 | grep -v "npm warn" || echo "Failed to install jsonlint"
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
