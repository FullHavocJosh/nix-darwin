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

  security.pam.services.sudo_local.touchIdAuth = true;
  security.sudo.extraConfig = ''
    Defaults timestamp_timeout=60
  '';

  # Prepend tap trust setup to the homebrew activation script so it runs BEFORE brew bundle.
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

        # Stash herdr's pre-upgrade version here, before `brew bundle`'s own
        # --upgrade sweep (homebrew.onActivation.upgrade = true, see
        # packages-tui.nix) potentially upgrades it. The later herdr-specific
        # check in system.activationScripts.script.text runs after brew bundle
        # has already completed, so comparing against a version captured at
        # that point would always see the post-upgrade version on both sides
        # of the diff -- silently skipping the live-handoff even when brew
        # bundle just upgraded herdr out from under a running session.
        # Lives under ~/.config/herdr/ (same dir as herdr's own config.toml,
        # dotfile-synced across machines) rather than /tmp, for persistence
        # and debuggability -- but it's gitignored, since this is per-device
        # runtime state (each machine's own herdr version), never something
        # to sync between devices via git.
        # Use absolute paths rather than `command -v`/bare `brew` here: this
        # runs via a plain `sudo -u user <cmd>`, not a login shell, so PATH
        # is whatever root's activation script started with -- it does NOT
        # include /opt/homebrew/bin. (The later script.text phase works
        # because it explicitly exports PATH with $HOMEBREW_PREFIX/bin
        # before its own herdr check.) Without this, the existence check
        # below always failed, so this file was never written, old version
        # always read back empty, and every darwin-rebuild looked like an
        # update -- forcing a live-handoff every single run.
        HERDR_STATE_DIR="$USER_HOME/.config/herdr"
        HERDR_VERSION_STATE_FILE="$HERDR_STATE_DIR/.version-before-rebuild"
        mkdir -p "$HERDR_STATE_DIR"
        if [ -x /opt/homebrew/bin/herdr ]; then
          HERDR_VERSION_BEFORE_REBUILD=$(sudo --set-home -u ${config.system.primaryUser} /opt/homebrew/bin/brew list --versions herdr 2>/dev/null || true)
          printf '%s\n' "$HERDR_VERSION_BEFORE_REBUILD" > "$HERDR_VERSION_STATE_FILE"
        else
          rm -f "$HERDR_VERSION_STATE_FILE"
        fi
        chown ${config.system.primaryUser} "$HERDR_VERSION_STATE_FILE" 2>/dev/null || true
  '';

  # Expose Homebrew and standard paths to GUI apps (e.g. Neovide finding nvim).
  # Must run as a user LaunchAgent so launchctl setenv applies to the user GUI session,
  # not the system domain (root's launchctl doesn't reach Finder-launched apps).
  launchd.user.agents.set-gui-path = {
    serviceConfig = {
      Label = "org.nixos.set-gui-path";
      ProgramArguments = [
        "/bin/sh"
        "-c"
        "/bin/launchctl setenv PATH /opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
      ];
      RunAtLoad = true;
    };
  };

  system.activationScripts.script.text = lib.mkAfter ''
        # Run user-specific configuration as the primary user
        USER_NAME="${config.system.primaryUser}"
        USER_HOME=$(eval echo ~$USER_NAME)
        
        sudo --set-home -u "$USER_NAME" bash <<'USERSCRIPT'
        if [ ! -L "$HOME/.gitignore_global" ] || [ "$(readlink "$HOME/.gitignore_global")" != "$HOME/nix-darwin/.gitignore_global" ]; then
          echo "Creating symlink for global gitignore..."
          ln -sf "$HOME/nix-darwin/.gitignore_global" "$HOME/.gitignore_global"
        fi

        # Claude Code scans ~/.claude/skills/ for direct subdirs with SKILL.md, not nested repos.
        # Skills are sourced from model-skills repos only; ~/.claude/skills/ is the target, never a source.
        mkdir -p "$HOME/.claude/skills"
        _link_skills_from_repo() {
          local repo="$1"
          # Never recurse into ~/.claude/skills itself — that is our target, not a source
          [ -d "$repo" ] || return 0
          [ "$(cd "$repo" && pwd -P)" = "$(cd "$HOME/.claude/skills" && pwd -P)" ] && return 0
          for skill_dir in "$repo"/*/; do
            [ -f "$skill_dir/SKILL.md" ] || continue
            local skill_name
            skill_name=$(basename "$skill_dir")
            local target="$HOME/.claude/skills/$skill_name"
            # A real directory here (e.g. one ralph-tui copied in on its own) would make `ln -sfn` nest the link
            # inside it instead of replacing it, and the repo copy would never be the one Claude Code loads.
            # Move it aside rather than delete it.
            if [ -d "$target" ] && [ ! -L "$target" ]; then
              local displaced="$HOME/.claude/.skills-displaced/$skill_name-$(date +%Y%m%d%H%M%S)"
              mkdir -p "$HOME/.claude/.skills-displaced"
              echo "Displacing real directory $target (the model-skills copy replaces it): $displaced"
              mv "$target" "$displaced"
            fi
            if [ ! -L "$target" ] || [ "$(readlink "$target")" != "$skill_dir" ]; then
              echo "Linking Claude skill: $skill_name → $skill_dir"
              ln -sfn "$skill_dir" "$target"
            fi
          done
        }
        for existing_link in "$HOME/.claude/skills"/*/; do
          [ -L "''${existing_link%/}" ] || continue
          link_name=$(basename "''${existing_link%/}")
          # Whole-repo convenience symlinks (below) have no SKILL.md of their own -- don't
          # treat them as stale skill links.
          case "$link_name" in
            model-skills-fullhavoc|model-skills-perfectserve) continue ;;
          esac
          if [ ! -f "''${existing_link}SKILL.md" ]; then
            echo "Removing stale Claude skill symlink: $link_name"
            rm "''${existing_link%/}"
          fi
        done
        _link_skills_from_repo "$HOME/model-skills-fullhavoc"
        _link_skills_from_repo "$HOME/model-skills-perfectserve"
        unset -f _link_skills_from_repo

        # Convenience symlinks to the whole model-skills repos (for browsing/editing the
        # source directly), alongside the per-skill symlinks above.
        _link_whole_repo() {
          local repo="$1"
          local name
          name=$(basename "$repo")
          [ -d "$repo" ] || return 0
          local target="$HOME/.claude/skills/$name"
          if [ ! -L "$target" ] || [ "$(readlink "$target")" != "$repo" ]; then
            echo "Linking model-skills repo: $name → $repo"
            ln -sfn "$repo" "$target"
          fi
        }
        _link_whole_repo "$HOME/model-skills-fullhavoc"
        _link_whole_repo "$HOME/model-skills-perfectserve"
        unset -f _link_whole_repo

        mkdir -p "$HOME/.claude/commands"
        _link_commands_from_repo() {
          local repo="$1"
          [ -d "$repo/.claude/commands" ] || return 0
          for cmd_file in "$repo/.claude/commands"/*.md; do
            [ -f "$cmd_file" ] || continue
            local cmd_name
            cmd_name=$(basename "$cmd_file")
            local target="$HOME/.claude/commands/$cmd_name"
            if [ ! -L "$target" ] || [ "$(readlink "$target")" != "$cmd_file" ]; then
              echo "Linking Claude command: $cmd_name"
              ln -sfn "$cmd_file" "$target"
            fi
          done
        }
        _link_commands_from_repo "$HOME/model-skills-fullhavoc"
        _link_commands_from_repo "$HOME/model-skills-perfectserve"
        unset -f _link_commands_from_repo

        if [ ! -L "$HOME/.claude/settings.local.json" ] || [ "$(readlink "$HOME/.claude/settings.local.json")" != "$HOME/nix-darwin/.claude/settings.local.json" ]; then
          echo "Creating symlink for Claude Code settings..."
          ln -sf "$HOME/nix-darwin/.claude/settings.local.json" "$HOME/.claude/settings.local.json"
        fi

        if command -v git &>/dev/null; then
          CURRENT_EXCLUDES=$(git config --global core.excludesfile 2>/dev/null || echo "")
          if [ "$CURRENT_EXCLUDES" != "$HOME/.gitignore_global" ]; then
            echo "Configuring git to use global gitignore..."
            git config --global core.excludesfile "$HOME/.gitignore_global"
          fi
        fi

        if command -v gh &>/dev/null; then
          if ! gh extension list 2>/dev/null | grep -q "gh-copilot"; then
            echo "Installing GitHub Copilot CLI extension..."
            gh extension install github/gh-copilot 2>/dev/null || echo "Failed to install gh-copilot extension"
          fi
        fi

        mkdir -p "$HOME/Library/Application Support/neovide"
        printf 'neovim-bin = "/opt/homebrew/bin/nvim"\n' > "$HOME/Library/Application Support/neovide/config.toml"

        HOMEBREW_PREFIX="/opt/homebrew"

        export PATH="$HOMEBREW_PREFIX/bin:$HOME/.cargo/bin:$HOME/go/bin:$PATH"

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
          # Dynamically discovers every repo directly under $HOME (anything with a
          # .git entry) instead of a hardcoded list -- so a newly cloned repo gets
          # picked up automatically on the next darwin-rebuild without editing this
          # file. Nested repos (2+ levels deep) are intentionally not touched here.
          for REPO_GIT_DIR in "$HOME"/*/.git; do
            [ -e "$REPO_GIT_DIR" ] || continue
            _update_repo_main "''${REPO_GIT_DIR%/.git}"
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

        # Determine which MCP servers this host should NOT run. Personal
        # machines (laptop/desktop) skip work-only servers (Jira, AWS/Terraform
        # infra tooling); the work machine skips personal homelab servers
        # (Hetzner/OPNsense/TrueNAS/AWX) plus Doppler (personal secrets flow
        # only). Same list gates both the Claude Code sync and the OpenCode
        # opencode.json patch below, so the two stay in lockstep.
        HOSTNAME_LOCAL=$(scutil --get LocalHostName 2>/dev/null)
        case "$HOSTNAME_LOCAL" in
          MacBookM2Pro*|MacMiniM1*)
            MCP_EXCLUDE_SERVERS="atlassian terraform-cloud terraform-hcp aws-terraform-mcp aws-pricing-mcp-server mcp-context-guardian-perfectserve"
            ;;
          MacBookM3Pro*)
            MCP_EXCLUDE_SERVERS="hetzner opnsense truenas awx doppler"
            ;;
          *)
            MCP_EXCLUDE_SERVERS=""
            ;;
        esac

        # Register context-mode with Claude Code if already installed
        if command -v context-mode &>/dev/null && command -v claude &>/dev/null; then
          if ! grep -q '"context-mode"' "$HOME/.claude.json" 2>/dev/null; then
            claude mcp add --scope user context-mode context-mode 2>/dev/null && \
              echo "Registered context-mode with Claude Code." || \
              echo "Failed to register context-mode with Claude Code."
          fi
        fi

        # mcp-stack-fullhavoc is a uv-managed Python project, not part of the
        # $HOME/mcp-* npm auto-build loop above -- sync its deps here so the
        # first real MCP handshake (Claude Code or opencode) isn't also the
        # first dependency resolve.
        if command -v uv &>/dev/null && [ -f "$HOME/mcp-stack-fullhavoc/pyproject.toml" ]; then
          echo "Syncing mcp-stack-fullhavoc dependencies..."
          uv sync --project "$HOME/mcp-stack-fullhavoc" && \
            echo "mcp-stack-fullhavoc dependencies up to date." || \
            echo "Failed to sync mcp-stack-fullhavoc dependencies"
        fi

        MCP_CONFIG="$HOME/nix-darwin/.config/mcp/claude-desktop-mcp.json"
        if command -v claude &>/dev/null && command -v jq &>/dev/null && [ -f "$MCP_CONFIG" ]; then
          echo "Syncing MCP servers from $MCP_CONFIG to Claude Code..."
          jq -r '.mcpServers | keys[]' "$MCP_CONFIG" | while read -r SERVER_NAME; do
            case " $MCP_EXCLUDE_SERVERS " in
              *" $SERVER_NAME "*)
                if grep -q "\"$SERVER_NAME\"" "$HOME/.claude.json" 2>/dev/null; then
                  claude mcp remove --scope user "$SERVER_NAME" 2>/dev/null && \
                    echo "  Removed $SERVER_NAME (excluded on this profile)." || \
                    echo "  Failed to remove $SERVER_NAME."
                else
                  echo "  $SERVER_NAME excluded on this profile, skipping."
                fi
                continue
                ;;
            esac

            if grep -q "\"$SERVER_NAME\"" "$HOME/.claude.json" 2>/dev/null; then
              # Two registrations that can never work: a command whose __HOME__ placeholder was never substituted
              # (ENOENT on a literal "__HOME__/..." path, seen on token-savior), and credential env values stored
              # empty because ''${VAR} was expanded by the activation shell, where those variables are not set. Drop
              # them; they are registered again below with the ''${VAR} placeholder stored literally.
              if jq -e --arg s "$SERVER_NAME" '((.mcpServers[$s].command // "") | contains("__HOME__")) or ([.mcpServers[$s].env // {} | to_entries[] | select(.value == "")] | length > 0)' "$HOME/.claude.json" >/dev/null 2>&1; then
                echo "  $SERVER_NAME was registered with an unsubstituted __HOME__ or empty env values; re-registering."
                claude mcp remove --scope user "$SERVER_NAME" 2>/dev/null || true
              else
                echo "  $SERVER_NAME already registered, skipping."
                continue
              fi
            fi

            COMMAND=$(jq -r ".mcpServers[\"$SERVER_NAME\"].command | gsub(\"__HOME__\"; \"$HOME\")" "$MCP_CONFIG")
            ARGS=$(jq -r ".mcpServers[\"$SERVER_NAME\"].args // [] | map(\"'\" + gsub(\"__HOME__\"; \"$HOME\") + \"'\") | join(\" \")" "$MCP_CONFIG")
            ENV_PAIRS=$(jq -r ".mcpServers[\"$SERVER_NAME\"].env // {} | to_entries | map(\"-e '\" + .key + \"=\" + (.value | gsub(\"__HOME__\"; \"$HOME\")) + \"'\") | join(\" \")" "$MCP_CONFIG")

            CMD="claude mcp add --scope user $SERVER_NAME $ENV_PAIRS -- $COMMAND $ARGS"
            eval "$CMD" 2>/dev/null && \
              echo "  Registered $SERVER_NAME with Claude Code." || \
              echo "  Failed to register $SERVER_NAME with Claude Code."
          done
        fi

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
          (cd "$HOME/nix-darwin" && ${pkgs.stow}/bin/stow -R .) || echo "Warning: failed to re-stow after unfolding \$HOME/.config"
        fi

        OPENCODE_CONFIG="$HOME/.config/opencode/opencode.json"
        REPO_OPENCODE_CONFIG="$HOME/nix-darwin/.config/opencode/opencode.json"
        if command -v jq &>/dev/null && [ -f "$REPO_OPENCODE_CONFIG" ]; then
          mkdir -p "$(dirname "$OPENCODE_CONFIG")"
          # Hard safety net: never rm+cp when the two paths are still the same
          # file (device+inode, via -ef) -- that's exactly the condition under
          # which rm would delete the git-tracked source out from under the
          # following cp, corrupting the repo's working tree. If the unfold
          # above ever regresses, fail loud here instead of deleting data.
          if [ -e "$OPENCODE_CONFIG" ] && [ "$OPENCODE_CONFIG" -ef "$REPO_OPENCODE_CONFIG" ]; then
            echo "Warning: $OPENCODE_CONFIG still resolves to the git-tracked file (unfold didn't take); skipping OpenCode config deployment this run to avoid corrupting the repo."
          else
            rm -f "$OPENCODE_CONFIG"
            cp "$REPO_OPENCODE_CONFIG" "$OPENCODE_CONFIG"
            # Skill directories are no longer injected into .skills.paths here --
            # the opencode-skillful plugin (see .config/opencode-skillful/config.json)
            # discovers them lazily via its own basePaths instead. This loop used to
            # unconditionally re-add $HOME/model-skills-* on every activation, which
            # silently reintroduced eager skill loading (and the ~17K token cost that
            # comes with it) on every darwin-rebuild regardless of what opencode.json's
            # own skills.paths was committed as.

            # OpenCode starts every MCP server it is given when it launches, which costs far more context than Claude
            # Code, which loads tools on demand. So OpenCode gets two kinds of entries: the always-needed servers in the
            # repo's opencode.json (mcp-stack-fullhavoc, plus context-guardian-perfectserve on the work profile), and one
            # mcp-lazy proxy that exposes two tools and starts each upstream server only when one of its tools is first
            # used. The proxy's server list, ~/.mcp-lazy/servers.json, is rebuilt on every rebuild from the servers Claude
            # Code has registered (profile exclusions already applied) minus the ones mcp-stack-fullhavoc replaces, so
            # both tools offer the same servers. mcp-lazy starts upstream servers with its own environment plus the env in
            # servers.json and does not expand ''${VAR}: credentials are left out of servers.json and are handed to the
            # proxy by name through its `environment` below ({env:NAME}, resolved by OpenCode at launch from the exports
            # in ~/.zshrc_personal). The tool index is cached by mcp-lazy; the first session after a change is slower.
            MCP_LAZY_JQ="$HOME/nix-darwin/.config/mcp/claude-to-mcp-lazy.jq"
            MCP_LAZY_SUPERSEDED='["mcp-context-guardian-fullhavoc","context-guardian","verbosity-guardian"]'
            if [ -f "$HOME/.claude.json" ] && [ -f "$MCP_LAZY_JQ" ]; then
              if LAZY=$(jq --arg home "$HOME" --argjson superseded "$MCP_LAZY_SUPERSEDED" -f "$MCP_LAZY_JQ" "$HOME/.claude.json" 2>/dev/null) && [ -n "$LAZY" ] && [ "$LAZY" != "{}" ]; then
                mkdir -p "$HOME/.mcp-lazy"
                if jq -n --argjson s "$LAZY" '{servers: $s}' > "$HOME/.mcp-lazy/servers.json.new"; then
                  mv "$HOME/.mcp-lazy/servers.json.new" "$HOME/.mcp-lazy/servers.json"
                  echo "mcp-lazy servers (started on demand by OpenCode): $(printf '%s' "$LAZY" | jq -r 'keys | join(", ")')"
                fi
                if [ -f "$MCP_CONFIG" ]; then
                  LAZY_ENV=$(jq '[.mcpServers[].env // {} | to_entries[] | select(.value | test("^\\$\\{[A-Za-z0-9_]+\\}$")) | .key] | unique | map({(.): "{env:\(.)}"}) | add // {}' "$MCP_CONFIG" 2>/dev/null)
                  if [ -n "$LAZY_ENV" ] && UPDATED=$(jq --argjson e "$LAZY_ENV" 'if .mcp["mcp-lazy"] then .mcp["mcp-lazy"].environment = ((.mcp["mcp-lazy"].environment // {}) + $e) else . end' "$OPENCODE_CONFIG" 2>/dev/null) && [ -n "$UPDATED" ]; then
                    printf '%s\n' "$UPDATED" > "$OPENCODE_CONFIG"
                  fi
                fi
              else
                echo "Warning: could not build the mcp-lazy server list from Claude Code; leaving ~/.mcp-lazy/servers.json as it is."
              fi
            fi

            for EXCLUDED in $MCP_EXCLUDE_SERVERS; do
              if jq -e --arg s "$EXCLUDED" '.mcp[$s]' "$OPENCODE_CONFIG" &>/dev/null; then
                UPDATED=$(jq --arg s "$EXCLUDED" '.mcp[$s].enabled = false' "$OPENCODE_CONFIG")
                printf '%s\n' "$UPDATED" > "$OPENCODE_CONFIG"
                echo "Disabled $EXCLUDED in OpenCode config (excluded on this profile)"
              fi
            done
          fi
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
          if ! command -v nexus &>/dev/null; then
            echo "Installing nexus-tui..."
            # Not on crates.io; pinned to a specific audited commit.
            # Audited at edd908b: Kubernetes TUI, no network/fs side effects beyond kubeconfig reads.
            # To update: review the diff from edd908b to the new commit before changing --rev.
            cargo install --git https://github.com/markx3/nexus-tui --rev edd908b26b4c19d9dd8e5cf3784f60f4b273669d 2>&1 || echo "Failed to install nexus-tui"
          fi
        fi

        # herdr is a brew package (see packages-tui.nix): its own self-update is disabled
        # on Homebrew installs ("run brew update && brew upgrade herdr" instead). But
        # homebrew.onActivation.upgrade = true (packages-tui.nix) already makes brew
        # bundle's own --upgrade sweep upgrade herdr, and that runs earlier in
        # activation (system.activationScripts.homebrew, before this script.text
        # phase) -- so by the time we'd capture a "before" version here, herdr is
        # already on the new binary. Comparing before/after at this point would
        # always see the same (already-upgraded) version on both sides and silently
        # skip the live-handoff even when brew bundle just upgraded herdr under a
        # running session. The real "before" version is stashed to
        # ~/.config/herdr/.version-before-rebuild (gitignored -- per-device
        # runtime state, not synced) up in the homebrew activation script,
        # before brew bundle runs at all -- compare against that instead.
        # `brew upgrade herdr` below is a fallback in case herdr didn't get upgraded
        # by the bundle sweep for some reason (e.g. temporarily dropped from the
        # Brewfile); harmless no-op otherwise since it's already current.
        # Hand each running named session's live panes/spaces/agents off to the
        # newly-installed binary instead of losing them to a cold restart.
        # `herdr server live-handoff` with no --session targets the unnamed "default"
        # session, which is never what's actually running (this machine's daily
        # driver is "dev") -- so loop over every session actually reporting
        # running:true instead of assuming one name.
        if command -v herdr &>/dev/null; then
          echo "Checking for herdr updates..."
          HERDR_VERSION_STATE_FILE="$HOME/.config/herdr/.version-before-rebuild"
          HERDR_OLD_VERSION=$(cat "$HERDR_VERSION_STATE_FILE" 2>/dev/null)
          brew upgrade herdr 2>&1 || echo "herdr already up to date or upgrade failed"
          HERDR_NEW_VERSION=$(brew list --versions herdr 2>/dev/null)
          rm -f "$HERDR_VERSION_STATE_FILE"
          if [ "$HERDR_OLD_VERSION" != "$HERDR_NEW_VERSION" ]; then
            echo "herdr updated ($HERDR_OLD_VERSION -> $HERDR_NEW_VERSION), handing off live sessions..."
            herdr session list --json 2>/dev/null | jq -r '.sessions[] | select(.running==true) | .name' | while read -r session_name; do
              herdr server live-handoff --session "$session_name" 2>&1 || echo "Failed to hand off herdr session '$session_name' to the updated binary"
            done
          else
            echo "herdr already up to date, skipping live-handoff"
          fi

          # Every live herdr pane keeps running the zsh it started with -- a
          # function/alias change from this rebuild (gpr/gpa/gpc, aistack, etc)
          # is invisible to it until something re-sources the dotfiles in that
          # shell, and so is a brand-new environment.variables entry (e.g.
          # AI_LOCAL_DEFAULT from laptop.nix/work.nix): /etc/zshenv only ever
          # runs its env-setting block once per shell process (guarded by
          # __ETC_ZSHENV_SOURCED/__NIX_DARWIN_SET_ENVIRONMENT_DONE), so a pane
          # opened before a var was added keeps missing it forever -- plain
          # `source ~/.zshrc` was confirmed live to NOT fix this (it doesn't
          # touch /etc/zshenv at all). Broadcast both refreshes on every
          # activation, not just when herdr itself updated above (dotfiles and
          # system env vars can both change on their own).
          #
          # Applies to every live pane, not just ones labeled "zsh" -- a pane
          # can have nvim/tuicr/btop/an AI agent running in it, and the goal is
          # to source the dotfiles in its underlying shell and leave whatever
          # was running exactly where it was, not skip the pane or replace what
          # it was doing. `herdr pane process-info` reports the real foreground
          # process (not the static "label", which is the pane's intended
          # purpose, not its live state) -- when it differs from the pane's own
          # shell_pid, something else owns the terminal right now.
          #
          # For those panes: suspend the foreground job with a literal Ctrl-Z
          # (0x1a) over `pane send-text` -- verified live against both a plain
          # `sleep` and a real ncurses app (btop): `pane send-keys <id> ctrl+z`
          # (the logical key name) measurably lags before the suspend lands, so
          # this polls process-info for it to actually settle back to the shell
          # rather than assuming it took effect immediately. If it never
          # settles (some apps disable SIGTSTP on purpose), the pane is left
          # completely alone -- better to skip a refresh than send
          # "source ~/.zshrc" as literal keystrokes into whatever's still
          # running there. Once settled: refresh env vars and source the
          # dotfiles, then `fg` to
          # resume the suspended job exactly where it left off -- confirmed
          # live that btop came back with its own window undisturbed, same
          # pid, not relaunched.
          #
          # One pane is never a suspend target: whichever one is itself mid-
          # `darwin-rebuild`, i.e. this very activation run, if it was launched
          # from inside a herdr pane. Suspending that foreground job would
          # suspend the activation script out from under itself. Matched by a
          # cmdline substring, not a pid (this script's own pid isn't visible
          # to a plain `herdr pane list` scan the way a shell job's is).
          echo "Refreshing herdr panes with latest dotfiles and env vars..."
          herdr pane list 2>/dev/null | jq -c '.result.panes[]?' | while read -r pane_json; do
            pane_id=$(echo "$pane_json" | jq -r '.pane_id')
            agent_status=$(echo "$pane_json" | jq -r '.agent_status // empty')
            # A "working" agent pane is mid-stream -- actively reading from its
            # provider's network connection, not just sitting at its own input
            # prompt. A suspend/resume pause is brief (under a second once it
            # lands) and a TCP socket tolerates that fine on its own, but there
            # is no way to rule out a provider- or client-side idle timeout
            # tripping during it, and this is exactly the kind of live session
            # a corrupted resume would actually cost something real. Skip it;
            # it will pick up the refresh once it goes idle and gets run again
            # (or the next rebuild).
            [ "$agent_status" = "working" ] && continue
            info=$(herdr pane process-info --pane "$pane_id" 2>/dev/null)
            shell_pid=$(echo "$info" | jq -r '.result.process_info.shell_pid // empty')
            fg_pid=$(echo "$info" | jq -r '.result.process_info.foreground_processes[0].pid // empty')
            fg_cmdline=$(echo "$info" | jq -r '.result.process_info.foreground_processes[0].cmdline // empty')
            [ -z "$shell_pid" ] && continue
            case "$fg_cmdline" in
              *darwin-rebuild*) continue ;;
            esac

            had_job=false
            if [ -n "$fg_pid" ] && [ "$fg_pid" != "$shell_pid" ]; then
              had_job=true
              herdr pane send-text "$pane_id" $'\x1a' >/dev/null 2>&1
              settled=false
              for _ in 1 2 3 4 5 6 7 8 9 10; do
                sleep 0.3
                now_pid=$(herdr pane process-info --pane "$pane_id" 2>/dev/null | jq -r '.result.process_info.foreground_processes[0].pid // empty')
                if [ "$now_pid" = "$shell_pid" ]; then
                  settled=true
                  break
                fi
              done
              if [ "$settled" != true ]; then
                echo "Herdr pane '$pane_id' did not yield its shell after Ctrl-Z -- leaving it alone"
                continue
              fi
            fi

            herdr pane run "$pane_id" 'set_env=$(grep -o "/nix/store/[^[:space:]]*-set-environment" /etc/zshenv 2>/dev/null); [ -n "$set_env" ] && source "$set_env"; source ~/.zshrc' >/dev/null 2>&1 || echo "Failed to refresh herdr pane '$pane_id'"
            if [ "$had_job" = true ]; then
              herdr pane run "$pane_id" "fg" >/dev/null 2>&1 || echo "Failed to resume foreground job in herdr pane '$pane_id'"
            fi
          done
        fi
    USERSCRIPT
  '';

  system.defaults = {
    NSGlobalDomain.AppleInterfaceStyle = "Dark";
    NSGlobalDomain.AppleIconAppearanceTheme = null;
    NSGlobalDomain.NSScrollAnimationEnabled = true;
    NSGlobalDomain.NSWindowResizeTime = 0.05;

    dock.autohide = true;
    dock.autohide-delay = 0.5;
    dock.autohide-time-modifier = 0.5;
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
    dock.expose-group-apps = true;
    dock.expose-animation-duration = 0.05;
    dock.minimize-to-application = false;
    dock.wvous-bl-corner = 1;
    dock.wvous-br-corner = 1;
    dock.wvous-tl-corner = 1;
    dock.wvous-tr-corner = 1;
    dock.show-process-indicators = true;
    dock.appswitcher-all-displays = false;
    dock.scroll-to-open = false;
    dock.mouse-over-hilite-stack = true;

    NSGlobalDomain._HIHideMenuBar = false;
    menuExtraClock.IsAnalog = false;
    menuExtraClock.ShowAMPM = false;
    menuExtraClock.ShowDate = 0;
    menuExtraClock.Show24Hour = false;
    menuExtraClock.ShowSeconds = false;
    menuExtraClock.ShowDayOfWeek = false;
    menuExtraClock.ShowDayOfMonth = false;
    menuExtraClock.FlashDateSeparators = false;

    finder.ShowPathbar = true;
    finder.ShowStatusBar = true;
    finder.AppleShowAllFiles = true;
    finder.AppleShowAllExtensions = true;
    finder.FXPreferredViewStyle = "Nlsv";
    finder.FXDefaultSearchScope = "SCcf";
    finder.FXEnableExtensionChangeWarning = false;
    finder._FXSortFoldersFirst = true;
    finder._FXSortFoldersFirstOnDesktop = true;
    finder._FXShowPosixPathInTitle = true;
    finder._FXEnableColumnAutoSizing = false;
    finder.QuitMenuItem = false;
    finder.CreateDesktop = false;
    finder.FXRemoveOldTrashItems = false;
    finder.NewWindowTarget = "iCloud Drive";
    finder.ShowExternalHardDrivesOnDesktop = false;
    finder.ShowHardDrivesOnDesktop = false;
    finder.ShowRemovableMediaOnDesktop = false;
    finder.ShowMountedServersOnDesktop = false;
    NSGlobalDomain.AppleShowAllFiles = true;
    NSGlobalDomain.AppleShowAllExtensions = true;

    loginwindow.GuestEnabled = false;

    trackpad.Clicking = false;
    trackpad.Dragging = false;
    trackpad.TrackpadRightClick = true;
    trackpad.TrackpadThreeFingerDrag = false;
    trackpad.TrackpadMomentumScroll = true;
    trackpad.TrackpadPinch = true;
    trackpad.TrackpadRotate = false;
    trackpad.TrackpadTwoFingerDoubleTapGesture = false;
    trackpad.TrackpadFourFingerHorizSwipeGesture = 0;
    trackpad.TrackpadFourFingerVertSwipeGesture = 0;
    trackpad.TrackpadFourFingerPinchGesture = 0;
    trackpad.DragLock = false;
    trackpad.TrackpadThreeFingerHorizSwipeGesture = 0;
    trackpad.TrackpadThreeFingerVertSwipeGesture = 0;
    trackpad.TrackpadTwoFingerFromRightEdgeSwipeGesture = 3;
    trackpad.TrackpadThreeFingerTapGesture = 0;
    trackpad.TrackpadCornerSecondaryClick = 0;
    trackpad.FirstClickThreshold = 1;
    trackpad.SecondClickThreshold = 1;
    trackpad.ActuateDetents = true;
    NSGlobalDomain.AppleEnableSwipeNavigateWithScrolls = false;
    NSGlobalDomain.NSWindowShouldDragOnGesture = true;

    NSGlobalDomain."com.apple.keyboard.fnState" = false;
    NSGlobalDomain.KeyRepeat = 2;
    NSGlobalDomain.InitialKeyRepeat = 15;
    hitoolbox.AppleFnUsageType = "Do Nothing";

    WindowManager.AutoHide = true;
    WindowManager.StandardHideDesktopIcons = true;
    WindowManager.HideDesktop = true;
    WindowManager.EnableStandardClickToShowDesktop = false;
    WindowManager.GloballyEnabled = false;
    WindowManager.AppWindowGroupingBehavior = false;
    WindowManager.EnableTilingByEdgeDrag = true;
    WindowManager.EnableTopTilingByEdgeDrag = true;
    WindowManager.EnableTilingOptionAccelerator = true;
    WindowManager.EnableTiledWindowMargins = true;
    WindowManager.StandardHideWidgets = false;
    WindowManager.StageManagerHideWidgets = false;

    NSGlobalDomain.ApplePressAndHoldEnabled = false;
    NSGlobalDomain.NSDocumentSaveNewDocumentsToCloud = true;
    NSGlobalDomain.NSAutomaticInlinePredictionEnabled = false;
    NSGlobalDomain.NSAutomaticSpellingCorrectionEnabled = false;
    NSGlobalDomain.NSAutomaticPeriodSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticCapitalizationEnabled = false;
    NSGlobalDomain.NSAutomaticDashSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticQuoteSubstitutionEnabled = false;
    NSGlobalDomain.AppleScrollerPagingBehavior = true;
    NSGlobalDomain.AppleShowScrollBars = "Automatic";
    NSGlobalDomain."com.apple.swipescrolldirection" = true;
    NSGlobalDomain."com.apple.sound.beep.volume" = 0.4346;

    screensaver.askForPassword = true;
    screensaver.askForPasswordDelay = 0;

    screencapture.type = "png";
    screencapture.disable-shadow = false;
    screencapture.include-date = true;
    screencapture.save-selections = true;
    screencapture.show-thumbnail = true;
    screencapture.target = "file";

    spaces.spans-displays = false;
    SoftwareUpdate.AutomaticallyInstallMacOSUpdates = false;
    LaunchServices.LSQuarantine = true;
    magicmouse.MouseButtonMode = "TwoButton";
  };

  networking.applicationFirewall = {
    enable = false;
    allowSigned = true;
    allowSignedApp = true;
    enableStealthMode = false;
    blockAllIncoming = false;
  };
}
