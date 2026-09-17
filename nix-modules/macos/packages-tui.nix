# TUI/CLI packages shared across ALL profiles (laptop, desktop, work)
# GUI applications are in packages-gui.nix (laptop only)
#
# PACKAGE POLICY: Prefer Homebrew for all new packages (brews/casks below).
# Only use environment.systemPackages for packages not available on Homebrew.
{
  pkgs,
  lib,
  username,
  ...
}:
let

  claudeTuiSetup = pkgs.writeShellScript "claude-tui-setup" ''
        #!/usr/bin/env bash
        set -euo pipefail

        SETTINGS_FILE="$HOME/.claude/settings.json"
        COMMANDS_DIR="$HOME/.claude/commands"
        SETUP_MARKER="$HOME/.claude/.claudetui-configured"

        if [ -f "$SETUP_MARKER" ] && [ -f "$SETTINGS_FILE" ]; then
          if grep -q '"statusLine"' "$SETTINGS_FILE" && \
             grep -q 'claudetui statusline' "$SETTINGS_FILE" && \
             [ -L "$COMMANDS_DIR/tui" ]; then
            echo "[claude-tui] Already configured, skipping setup"
            exit 0
          fi
        fi

        echo "[claude-tui] Configuring Claude Code integration..."

        if [ ! -d "$HOME/.claude" ]; then
          echo "[claude-tui] WARNING: ~/.claude directory not found — Claude Code may not be installed"
          exit 0
        fi

        if ! command -v claudetui &>/dev/null; then
          echo "[claude-tui] WARNING: claudetui command not found — installation may be incomplete"
          exit 0
        fi

        export STATUSLINE_MODE="full"
        export PATH="/opt/homebrew/bin:$PATH"
        SETUP_SCRIPT=$(mktemp)
        cat > "$SETUP_SCRIPT" << 'SETUPEOF'
    #!/usr/bin/env bash
    set -euo pipefail

    SETTINGS_FILE="$HOME/.claude/settings.json"
    COMMANDS_DIR="$HOME/.claude/commands"
    INSTALL_DIR="''${INSTALL_DIR:-/opt/homebrew/opt/claude-tui/libexec}"

    python3 << 'PYEOF'
    import json
    import os
    from pathlib import Path

    settings_file = os.path.expanduser("~/.claude/settings.json")

    settings = {}
    if os.path.exists(settings_file):
        try:
            with open(settings_file) as f:
                settings = json.load(f)
        except (json.JSONDecodeError, IOError):
            backup = settings_file + ".backup"
            if os.path.exists(settings_file):
                os.rename(settings_file, backup)

    mode = os.environ.get("STATUSLINE_MODE", "full")
    statusline_cmd = "claudetui statusline"
    if mode == "compact":
        statusline_cmd += " --compact"

    settings["statusLine"] = {
        "type": "command",
        "command": statusline_cmd,
    }

    hooks = settings.get("hooks", {})

    hook_configs = [
        {
            "event": "SessionStart",
            "matcher": "",
            "command": "claudetui hook session-heatmap",
        },
        {
            "event": "PreToolUse",
            "matcher": "Edit|Write",
            "command": "claudetui hook pre-edit-churn",
        },
        {
            "event": "PostToolUse",
            "matcher": "Edit|Write",
            "command": "claudetui hook post-edit-deps",
        },
    ]

    for cfg in hook_configs:
        event = cfg["event"]
        if event not in hooks:
            hooks[event] = []

        already_exists = False
        for rule in hooks[event]:
            for h in rule.get("hooks", []):
                if h.get("command") == cfg["command"]:
                    already_exists = True
                    break
            if already_exists:
                break

        if not already_exists:
            hooks[event].append({
                "matcher": cfg["matcher"],
                "hooks": [{"type": "command", "command": cfg["command"]}],
            })

    settings["hooks"] = hooks

    Path(settings_file).parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_file + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    os.replace(tmp, settings_file)
    PYEOF

    mkdir -p "$COMMANDS_DIR"
    if [ -L "$COMMANDS_DIR/tui" ]; then
        rm "$COMMANDS_DIR/tui"
    fi
    ln -sfn "$INSTALL_DIR/claude-code-commands/tui" "$COMMANDS_DIR/tui"

    echo "[claude-tui] Configuration complete"
    SETUPEOF

        chmod +x "$SETUP_SCRIPT"
        bash "$SETUP_SCRIPT"
        rm -f "$SETUP_SCRIPT"

        touch "$SETUP_MARKER"
        echo "[claude-tui] Setup completed successfully"
  '';

  # Vetted 2026-09-16: all four are real, actively maintained OSS projects
  # (see PR description for the per-tool footprint writeup). token-savior is
  # registered as an MCP server via claude-desktop-mcp.json; this script only
  # does the parts that json sync can't (venv creation, npm global install,
  # the caveman plugin, and the CLAUDE.md rules drop-in).
  tokenOptimizationSetup = pkgs.writeShellScript "token-optimization-setup" ''
        #!/usr/bin/env bash
        set -uo pipefail

        MARKER_DIR="$HOME/.claude/.token-optimization"
        mkdir -p "$MARKER_DIR"

        # --- token-savior: symbol-navigation MCP server, isolated venv ---
        if [ ! -x "$HOME/bench/venv-tokensavior/bin/token-savior" ]; then
          echo "[token-optimization] Installing token-savior..."
          if python3 -m venv "$HOME/bench/venv-tokensavior" && \
             "$HOME/bench/venv-tokensavior/bin/pip" install --quiet 'token-savior-recall[mcp]'; then
            echo "[token-optimization] token-savior installed."
          else
            echo "WARNING: token-savior install failed" >&2
          fi
        fi

        # --- claude-token-efficient: terseness rules dropped into global CLAUDE.md ---
        CLAUDE_MD="$HOME/.claude/CLAUDE.md"
        RULES_MARKER="<!-- claude-token-efficient rules (github.com/drona23/claude-token-efficient) -->"
        mkdir -p "$(dirname "$CLAUDE_MD")"
        if [ ! -f "$CLAUDE_MD" ] || ! grep -qF "$RULES_MARKER" "$CLAUDE_MD"; then
          echo "[token-optimization] Adding claude-token-efficient rules to CLAUDE.md..."
          RULES=$(curl -fsSL https://raw.githubusercontent.com/drona23/claude-token-efficient/main/CLAUDE.md 2>/dev/null)
          if [ -n "$RULES" ]; then
            {
              echo ""
              echo "$RULES_MARKER"
              echo "$RULES"
            } >> "$CLAUDE_MD"
            echo "[token-optimization] CLAUDE.md updated."
          else
            echo "WARNING: could not fetch claude-token-efficient rules" >&2
          fi
        fi

        # --- token-optimizer-mcp: caching MCP + hooks, global npm install ---
        if ! npm ls -g @ooples/token-optimizer-mcp &>/dev/null; then
          echo "[token-optimization] Installing token-optimizer-mcp..."
          npm install -g @ooples/token-optimizer-mcp 2>&1 || echo "WARNING: token-optimizer-mcp install failed" >&2
        fi
        if [ ! -f "$MARKER_DIR/token-optimizer-hooks-installed" ]; then
          NPM_PREFIX=$(npm config get prefix 2>/dev/null || echo "/opt/homebrew")
          HOOKS_SCRIPT="$NPM_PREFIX/lib/node_modules/@ooples/token-optimizer-mcp/install-hooks.sh"
          if [ -f "$HOOKS_SCRIPT" ]; then
            echo "[token-optimization] Installing token-optimizer-mcp hooks..."
            if bash "$HOOKS_SCRIPT" --skip-mcp-check 2>&1; then
              touch "$MARKER_DIR/token-optimizer-hooks-installed"
              echo "[token-optimization] token-optimizer-mcp hooks installed."
            else
              echo "WARNING: token-optimizer-mcp hooks install failed" >&2
            fi
          fi
        fi

        # --- caveman: Claude Code plugin (skill + hooks + statusline) ---
        if command -v claude &>/dev/null && [ ! -f "$MARKER_DIR/caveman-plugin-installed" ]; then
          echo "[token-optimization] Installing caveman plugin..."
          claude plugin marketplace add JuliusBrussee/caveman 2>&1 || true
          if claude plugin install caveman@caveman 2>&1; then
            touch "$MARKER_DIR/caveman-plugin-installed"
            echo "[token-optimization] caveman plugin installed."
          else
            echo "WARNING: caveman plugin install failed" >&2
          fi
        fi
        mkdir -p "$HOME/.config/caveman"
        if [ ! -f "$HOME/.config/caveman/config.json" ]; then
          cat > "$HOME/.config/caveman/config.json" <<'JSON'
    {"defaultMode": "ultra"}
    JSON
        fi
  '';
in
{
  # Packages not available on Homebrew — add here only as a last resort.
  environment.systemPackages = with pkgs; [
    nil
    nixd
  ];

  homebrew = {
    enable = true;
    taps = [
      "warrensbox/tap"
      "xykong/tap"
      "slima4/claude-tui"
      "seunggabi/tap"
      "agavra/tap"
    ];
    brews = [
      "ansible"
      "ansible-lint"
      "argocd"
      "atuin"
      "bash-language-server"
      "btop"
      "cava"
      "cmake"
      "coreutils"
      "djlint"
      "dockerfile-language-server"
      "exiftool"
      "eza"
      "fastfetch"
      "fd"
      "fzf"
      "gh"
      "go"
      "golangci-lint"
      "golangci-lint-langserver"
      "gopls"
      "graphviz"
      "hadolint"
      "helm"
      "herdr"
      "jq"
      "jsonlint"
      "k9s"
      "kubectl"
      "lazygit"
      "lua-language-server"
      "luarocks"
      "mas"
      "mpv"
      "neovim"
      "nixfmt"
      "node@22"
      "opencode"
      "opentofu"
      "podman"
      "prettier"
      "python-lsp-server"
      "python3"
      "ripgrep"
      "ruff"
      "rust"
      "rust-analyzer"
      "shfmt"
      "solargraph"
      "speedtest-cli"
      "sshpass"
      "starship"
      "stow"
      "stylua"
      "superfile"
      "syncthing"
      "taplo"
      "tealdeer"
      "telnet"
      "terraform-inventory"
      "terraform-ls"
      "terraform-lsp"
      "terraformer"
      "tflint"
      "typescript"
      "tree-sitter"
      "typescript-language-server"
      "uv"
      "vscode-langservers-extracted"
      "watch"
      "yaml-language-server"
      "yamllint"
      "zoxide"
      "zplug"
      "ansible-language-server"
      "slima4/claude-tui/claude-tui"
      "agavra/tap/tuicr"
    ];
    casks = [
      "ghostty"
      "warrensbox/tap/tfswitch"
      "claude-code"
      "font-hack-nerd-font"
      "font-jetbrains-mono-nerd-font"
    ];
    masApps = { };
    onActivation.cleanup = "none";
    onActivation.extraFlags = [ "--force" ];
    onActivation.autoUpdate = true;
    onActivation.upgrade = true;
  };

  # Runs before brew bundle so Homebrew can link without conflict.
  system.activationScripts.homebrew.text = lib.mkBefore ''
    if [ -L /opt/homebrew/bin/jsonlint ] && readlink /opt/homebrew/bin/jsonlint | grep -q node_modules; then
      echo "Removing npm-installed jsonlint symlink (replaced by Homebrew)..."
      rm -f /opt/homebrew/bin/jsonlint
    fi
  '';

  # Was "packagesUserConfig" -- a name nix-darwin's own activation-scripts.nix
  # never references (its system.activationScripts.script.text hardcodes a
  # fixed list of known names: checks, groups, users, homebrew,
  # postActivation, etc). types.attrsOf submodule happily accepts any
  # attribute name, including ones nothing consumes, so this evaluated fine
  # and `nix eval` on it showed the right content, but it was never part of
  # config.system.build.toplevel's actual closure -- confirmed by comparing
  # .drvPath across commits: editing this text never changed the derivation,
  # while editing system.activationScripts.homebrew.text (a real, referenced
  # name) always did. Every darwin-rebuild switch has silently no-op'd this
  # whole block since it was introduced -- claudeTuiSetup, the Opcode
  # auto-install, and now token-optimization-setup never actually ran.
  # postActivation IS one of the real names (nix-darwin's own doc comment on
  # it: "Extra activation scripts, that can be customized by users").
  system.activationScripts.postActivation.text = lib.mkAfter ''
        # This whole block runs as root (nix-darwin activation always does),
        # so `id -un` here returns "root", not the real login user -- that
        # made `sudo -u "$USER_NAME"` a no-op (already root) and left $HOME
        # as /var/root for everything below, e.g. token-savior's venv landed
        # at /var/root/bench (using macOS's ancient system python3, whose old
        # pip couldn't even resolve the package) instead of ~/bench. Use the
        # module's own username argument instead, same as config.nix does via
        # config.system.primaryUser. --set-home makes sudo actually reset
        # $HOME for the target user; without it, sudo -u alone does not.
        USER_NAME="${username}"
        USER_HOME=$(eval echo "~$USER_NAME")

        sudo --set-home -u "$USER_NAME" bash <<'USERSCRIPT'
        # sudo -u spawns a non-login, non-interactive shell -- it never reads
        # .zprofile/.zshrc, so PATH here is whatever sudo's secure_path
        # default is (typically /usr/bin:/bin:/usr/sbin:/sbin), NOT Homebrew's
        # bin dirs. Confirmed: this is why brew/npm/node all came back
        # "command not found" here despite being freshly installed moments
        # earlier in this same activation run.
        export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

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

        if [ -f "$HOME/.config/opencode/opencode.json" ]; then
          echo "Patching opencode.json with correct home path..."
          ${pkgs.gnused}/bin/sed -i "s|__HOME__|$HOME|g" "$HOME/.config/opencode/opencode.json"
        fi

        if ! command -v claude-dashboard &>/dev/null; then
          echo "Installing claude-dashboard..."
          brew install seunggabi/tap/claude-dashboard 2>&1 || true
        fi

        (
          ${claudeTuiSetup}
        ) || echo "WARNING: claude-tui setup failed — continuing activation" >&2

        (
          ${tokenOptimizationSetup}
        ) || echo "WARNING: token-optimization setup failed — continuing activation" >&2

        (
          OPCODE_APP="/Applications/opcode.app"
          if [ ! -d "$OPCODE_APP" ]; then
            echo "Installing Opcode desktop app..."
            # Pinned version — update OPCODE_PINNED_VERSION and OPCODE_PINNED_SHA256 together when upgrading.
            # Recompute checksum with: curl -fsSL <dmg-url> | shasum -a 256
            OPCODE_PINNED_VERSION="v0.2.0"
            OPCODE_PINNED_SHA256="9868d20b46fa3fba134049e931ef745571805b0e1919e7bad807ca454f5932f8"
            OPCODE_DMG_URL="https://github.com/winfunc/opcode/releases/download/$OPCODE_PINNED_VERSION/opcode_''${OPCODE_PINNED_VERSION}_macos_universal.dmg"
            echo "Downloading Opcode $OPCODE_PINNED_VERSION..."
            OPCODE_TMPDIR=$(mktemp -d)
            curl -fsSL "$OPCODE_DMG_URL" -o "$OPCODE_TMPDIR/opcode.dmg"
            OPCODE_ACTUAL=$(shasum -a 256 "$OPCODE_TMPDIR/opcode.dmg" | awk '{print $1}')
            if [ "$OPCODE_ACTUAL" != "$OPCODE_PINNED_SHA256" ]; then
              echo "ERROR: Opcode DMG checksum mismatch — aborting install" >&2
              rm -rf "$OPCODE_TMPDIR"
              exit 1
            fi
            MOUNT="$OPCODE_TMPDIR/mnt"
            mkdir -p "$MOUNT"
            hdiutil attach "$OPCODE_TMPDIR/opcode.dmg" -nobrowse -mountpoint "$MOUNT" || { echo "ERROR: Failed to mount Opcode DMG" >&2; rm -rf "$OPCODE_TMPDIR"; exit 1; }
            [ -d "$MOUNT/opcode.app" ] || { echo "ERROR: opcode.app not found in mounted DMG at $MOUNT" >&2; hdiutil detach "$MOUNT" -quiet; rm -rf "$OPCODE_TMPDIR"; exit 1; }
            cp -R "$MOUNT/opcode.app" /Applications/
            hdiutil detach "$MOUNT" -quiet
            rm -rf "$OPCODE_TMPDIR"
            echo "Opcode desktop app installed."
          fi
        ) || echo "WARNING: Opcode install failed — continuing activation" >&2
    USERSCRIPT
  '';

}
