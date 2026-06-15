{
  pkgs,
  lib,
  config,
  ...
}:
{
  nixpkgs.config.allowUnfree = true;
  nixpkgs.hostPlatform = "aarch64-darwin";
  nix.settings.experimental-features = "nix-command flakes";
  programs.zsh.enable = true;
  system.stateVersion = 5;

  # Prepend tap trust setup to the homebrew activation script so it runs BEFORE brew bundle.
  # Writes ~/.homebrew/trust.json directly (no brew binary needed, runs as root).
  system.activationScripts.homebrew.text = lib.mkBefore ''
        USER_HOME=$(eval echo ~${config.system.primaryUser})
        TRUST_FILE="$USER_HOME/.homebrew/trust.json"
        mkdir -p "$USER_HOME/.homebrew"
        /usr/bin/python3 -c "
    import json, os
    tf = '$TRUST_FILE'
    taps = 'dopplerhq/cli minio/stable nikitabobko/tap seunggabi/tap slima4/claude-tui vitobotta/tap warrensbox/tap xykong/tap'.split()
    try:
        with open(tf) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d['trustedtaps'] = sorted(set(d.get('trustedtaps', []) + taps))
    with open(tf, 'w') as f:
        json.dump(d, f, indent=2)
        f.write('\n')
    "
        chown ${config.system.primaryUser} "$TRUST_FILE"
  '';

  system.activationScripts.script.text = lib.mkAfter ''
        # Run user-specific configuration as the primary user
        USER_NAME="${config.system.primaryUser}"
        USER_HOME=$(eval echo ~$USER_NAME)
        
        sudo --set-home -u "$USER_NAME" bash <<'USERSCRIPT'
        # Symlink global gitignore from nix-darwin to home directory
        if [ ! -L "$HOME/.gitignore_global" ] || [ "$(readlink "$HOME/.gitignore_global")" != "$HOME/nix-darwin/.gitignore_global" ]; then
          echo "Creating symlink for global gitignore..."
          ln -sf "$HOME/nix-darwin/.gitignore_global" "$HOME/.gitignore_global"
        fi

        # Symlink Claude Code skills — prefer model-skills repos over nix-darwin fallback
        CLAUDE_SKILLS_SRC="$HOME/nix-darwin/.claude/skills"
        if [ -d "$HOME/model-skills-fullhavoc" ]; then
          CLAUDE_SKILLS_SRC="$HOME/model-skills-fullhavoc"
        elif [ -d "$HOME/model-skills-perfectserve" ]; then
          CLAUDE_SKILLS_SRC="$HOME/model-skills-perfectserve"
        fi
        if [ ! -L "$HOME/.claude/skills" ] || [ "$(readlink "$HOME/.claude/skills")" != "$CLAUDE_SKILLS_SRC" ]; then
          echo "Creating symlink for Claude Code skills → $CLAUDE_SKILLS_SRC"
          ln -sfn "$CLAUDE_SKILLS_SRC" "$HOME/.claude/skills"
        fi

        # Symlink Claude Code settings from nix-darwin
        if [ ! -L "$HOME/.claude/settings.local.json" ] || [ "$(readlink "$HOME/.claude/settings.local.json")" != "$HOME/nix-darwin/.claude/settings.local.json" ]; then
          echo "Creating symlink for Claude Code settings..."
          ln -sf "$HOME/nix-darwin/.claude/settings.local.json" "$HOME/.claude/settings.local.json"
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

        # Update all tracked repos to latest main, preserving local branch/changes
        if command -v git &>/dev/null; then
          _update_repo_main() {
            local repo_path="$1"
            local repo_name
            repo_name=$(basename "$repo_path")

            if [ ! -d "$repo_path/.git" ]; then
              echo "  $repo_name: not present, skipping."
              return 0
            fi

            echo "── $repo_name ──"

            local current_branch
            current_branch=$(git -C "$repo_path" symbolic-ref --short HEAD 2>/dev/null)
            if [ -z "$current_branch" ]; then
              echo "  Detached HEAD, skipping."
              return 0
            fi

            local stash_created=0
            if ! git -C "$repo_path" diff --quiet HEAD 2>/dev/null; then
              git -C "$repo_path" stash push -m "darwin-rebuild auto-stash $(date +%Y%m%d-%H%M%S)" \
                && stash_created=1 \
                && echo "  Stashed uncommitted changes."
            fi

            local main_branch
            if git -C "$repo_path" rev-parse --verify main &>/dev/null; then
              main_branch="main"
            elif git -C "$repo_path" rev-parse --verify master &>/dev/null; then
              main_branch="master"
            else
              echo "  No main/master branch found, skipping."
              [ "$stash_created" -eq 1 ] && git -C "$repo_path" stash pop
              return 0
            fi

            if [ "$current_branch" != "$main_branch" ]; then
              git -C "$repo_path" checkout "$main_branch" || {
                echo "  Failed to checkout $main_branch, aborting."
                [ "$stash_created" -eq 1 ] && git -C "$repo_path" stash pop
                return 1
              }
            fi

            git -C "$repo_path" pull \
              && git -C "$repo_path" submodule update --init --recursive \
              || echo "  Warning: pull failed for $repo_name (SSH agent may not be available)."

            if [ "$current_branch" != "$main_branch" ]; then
              git -C "$repo_path" checkout "$current_branch" \
                || echo "  Warning: failed to return to $current_branch."
            fi

            if [ "$stash_created" -eq 1 ]; then
              git -C "$repo_path" stash pop \
                || echo "  Warning: stash pop failed — run: git -C '$repo_path' stash pop"
            fi

            echo "  Done."
          }

          echo "Updating tracked repositories to latest main..."
          for TRACKED_REPO in \
            "$HOME/nix-darwin" \
            "$HOME/home-infrastructure" \
            "$HOME/mcp-context-guardian-fullhavoc" \
            "$HOME/mcp-context-guardian-perfectserve" \
            "$HOME/model-skills-fullhavoc" \
            "$HOME/model-skills-perfectserve" \
            "$HOME/Infrastructure-Terrakube" \
            "$HOME/Infrastructure-Ansible"; do
            _update_repo_main "$TRACKED_REPO"
          done
          unset -f _update_repo_main
          echo "Finished updating repositories."
        fi

        if command -v npm &>/dev/null && command -v node &>/dev/null; then
          MCP_FOUND=0
          for MCP_DIR in "$HOME"/mcp-*/; do
            [ -d "$MCP_DIR" ] || continue
            [ -f "$MCP_DIR/package.json" ] || continue
            MCP_FOUND=1
            MCP_NAME=$(basename "$MCP_DIR")
            MCP_DIST="''${MCP_DIR%/}/dist/index.js"
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
              if ! grep -q "\"$MCP_NAME\"" "$HOME/.claude.json" 2>/dev/null; then
                claude mcp add --scope user "$MCP_NAME" node "$MCP_DIST" 2>/dev/null && \
                  echo "Registered $MCP_NAME with Claude Code." || \
                  echo "Failed to register $MCP_NAME with Claude Code."
              fi
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

        # Register context-mode with Claude Code if already installed
        if command -v context-mode &>/dev/null && command -v claude &>/dev/null; then
          if ! grep -q '"context-mode"' "$HOME/.claude.json" 2>/dev/null; then
            claude mcp add --scope user context-mode context-mode 2>/dev/null && \
              echo "Registered context-mode with Claude Code." || \
              echo "Failed to register context-mode with Claude Code."
          fi
        fi

        # Sync MCP servers from claude-desktop-mcp.json into Claude Code (global scope)
        MCP_CONFIG="$HOME/nix-darwin/.config/mcp/claude-desktop-mcp.json"
        if command -v claude &>/dev/null && command -v jq &>/dev/null && [ -f "$MCP_CONFIG" ]; then
          echo "Syncing MCP servers from $MCP_CONFIG to Claude Code..."
          jq -r '.mcpServers | keys[]' "$MCP_CONFIG" | while read -r SERVER_NAME; do
            if grep -q "\"$SERVER_NAME\"" "$HOME/.claude.json" 2>/dev/null; then
              echo "  $SERVER_NAME already registered, skipping."
              continue
            fi

            COMMAND=$(jq -r ".mcpServers[\"$SERVER_NAME\"].command" "$MCP_CONFIG")
            ARGS=$(jq -r ".mcpServers[\"$SERVER_NAME\"].args // [] | map(\"'\" + gsub(\"__HOME__\"; \"$HOME\") + \"'\") | join(\" \")" "$MCP_CONFIG")
            ENV_PAIRS=$(jq -r ".mcpServers[\"$SERVER_NAME\"].env // {} | to_entries | map(\"-e \" + .key + \"=\" + (.value | gsub(\"__HOME__\"; \"$HOME\"))) | join(\" \")" "$MCP_CONFIG")

            CMD="claude mcp add --scope user $SERVER_NAME $ENV_PAIRS -- $COMMAND $ARGS"
            eval "$CMD" 2>/dev/null && \
              echo "  Registered $SERVER_NAME with Claude Code." || \
              echo "  Failed to register $SERVER_NAME with Claude Code."
          done
        fi

        # Inject model-skills repo paths into OpenCode skills.paths if not already present
        OPENCODE_CONFIG="$HOME/.config/opencode/opencode.json"
        if command -v jq &>/dev/null && [ -f "$OPENCODE_CONFIG" ]; then
          for SKILLS_REPO in "$HOME/model-skills-fullhavoc" "$HOME/model-skills-perfectserve"; do
            [ -d "$SKILLS_REPO" ] || continue
            if ! jq -e --arg p "$SKILLS_REPO" '(.skills.paths // []) | contains([$p])' "$OPENCODE_CONFIG" &>/dev/null; then
              UPDATED=$(jq --arg p "$SKILLS_REPO" '.skills.paths = ((.skills.paths // []) + [$p] | unique)' "$OPENCODE_CONFIG")
              printf '%s\n' "$UPDATED" > "$OPENCODE_CONFIG"
              echo "Added $SKILLS_REPO to OpenCode skills.paths"
            fi
          done
        fi

        if command -v uv &>/dev/null; then
          if ! uv tool list 2>/dev/null | grep -q "^unmcp "; then
            echo "Installing unmcp CLI tool..."
            uv tool install unmcp 2>&1 || echo "Failed to install unmcp"
          fi
          if ! uv tool list 2>/dev/null | grep -q "^claude-code-config "; then
            echo "Installing claude-code-config..."
            uv tool install claude-code-config 2>&1 || echo "Failed to install claude-code-config"
          fi
        fi

        if command -v go &>/dev/null; then
          if ! command -v claude-session-manager-tui &>/dev/null; then
            echo "Installing claude-session-manager-tui..."
            # Pinned to audited commit f114e7d (2026-04-01); no tagged releases exist upstream.
            # To update: review diff from f114e7d to new commit before changing the hash.
            go install github.com/borball/claude-session-manager-tui@f114e7d7e0d78e10087692a10724f2a7383edfd3 2>&1 || echo "Failed to install claude-session-manager-tui"
          fi
        fi

        if command -v cargo &>/dev/null; then
          if ! command -v nexus-tui &>/dev/null; then
            echo "Installing nexus-tui..."
            # Not on crates.io; pinned to a specific audited commit.
            # Audited at edd908b: Kubernetes TUI, no network/fs side effects beyond kubeconfig reads.
            # To update: review the diff from edd908b to the new commit before changing --rev.
            cargo install --git https://github.com/markx3/nexus-tui --rev edd908b26b4c19d9dd8e5cf3784f60f4b273669d 2>&1 || echo "Failed to install nexus-tui"
          fi
        fi
    USERSCRIPT
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
