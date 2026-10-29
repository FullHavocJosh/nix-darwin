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

  # See claude-tui-usage-patch.py: single labeled usage bar on the compact
  # statusline, no model name.
  claudeTuiUsagePatchScript = pkgs.writeText "claude-tui-usage-patch.py" (
    builtins.readFile ./claude-tui-usage-patch.py
  );

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

        export STATUSLINE_MODE="compact"
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

    mode = os.environ.get("STATUSLINE_MODE", "compact")
    statusline_cmd = "claudetui statusline"
    if mode == "compact":
        statusline_cmd += " --compact"

    settings["statusLine"] = {
        "type": "command",
        "command": statusline_cmd,
        "refreshInterval": 10,
    }

    # claudetui's hooks (session heatmap, edit churn, edit deps) are not installed: they added ~1.5K tokens to every
    # session start and notes to most edits, re-read on every later turn, for advice that was rarely acted on.

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

  # Keeps ~/.claude/settings.json free of hooks from retired tools, routes web search through Lumo, and enforces the
  # edit routing (edit_router_hook.py; CLAUDE_EDIT_ROUTER=off turns it off for a session):
  #   - removes token-optimizer-mcp's hooks and claude-tui's hooks (see tokenOptimizationSetup / claudeTuiSetup)
  #   - denies the built-in WebSearch; the lumo MCP server (.config/lumo/lumo_mcp.py) answers web questions instead.
  #     WebFetch stays allowed for reading one exact page.
  # Silent when already in place.
  claudeSettingsCleanup = pkgs.writeShellScript "claude-settings-cleanup" ''
    set -euo pipefail
    path="$HOME/.claude/settings.json"
    [ -f "$path" ] || exit 0
    python3 - "$path" <<'PYEOF'
    import json, os, sys
    path = sys.argv[1]
    with open(path) as f:
        settings = json.load(f)
    before = json.dumps(settings, sort_keys=True)
    def retired(cmd):
        return "token-optimizer" in cmd or cmd.startswith("claudetui hook")
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        kept = []
        for rule in hooks[event]:
            rule["hooks"] = [h for h in rule.get("hooks", []) if not retired(h.get("command", ""))]
            if rule["hooks"]:
                kept.append(rule)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    deny = settings.setdefault("permissions", {}).setdefault("deny", [])
    if "WebSearch" not in deny:
        deny.append("WebSearch")
    # The free tools that take work from Claude run without a permission prompt.
    allow = settings["permissions"].setdefault("allow", [])
    if "mcp__bigpickle__bigpickle_edit" in allow:  # renamed to oczen_edit
        allow.remove("mcp__bigpickle__bigpickle_edit")
    for tool in ("mcp__lumo__lumo_search", "mcp__local-edit__local_edit", "mcp__oczen__oczen_edit"):
        if tool not in allow:
            allow.append(tool)
    # edit_router_hook.py: the third file edited by hand in one request goes to local_edit / oczen_edit.
    router = "python3 \"$HOME/.config/aistack/edit_router_hook.py\""
    if not any(h.get("command") == router for r in hooks.get("PreToolUse", []) for h in r.get("hooks", [])):
        hooks.setdefault("PreToolUse", []).append(
            {"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [{"type": "command", "command": router, "timeout": 10}]})
        settings["hooks"] = hooks
    if json.dumps(settings, sort_keys=True) != before:
        with open(path + ".tmp", "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        os.replace(path + ".tmp", path)
        print("[claude] Updated settings.json: retired hooks removed, WebSearch denied, edit routing enforced")
    PYEOF
  '';

  # Advisor mode (.config/aistack/advisor_hook.py, on by default in every session): Claude reads, searches and reviews,
  # and hands the user every change as a command or diff with an explanation, to run themselves as `! <command>`.
  #   - registers advisor_hook.py as a PreToolUse hook on every tool
  #   - links the Advisor output style (.config/aistack/advisor-style.md) and selects it when no style is set
  #   - links ~/.local/bin/advisor, the per-session switch: `! advisor off|on|status`
  # CLAUDE_ADVISOR=off claude starts a session without it. Silent when already in place.
  claudeAdvisorSetup = pkgs.writeShellScript "claude-advisor-setup" ''
    set -euo pipefail
    mkdir -p "$HOME/.claude/output-styles" "$HOME/.local/bin"
    ln -sfn "$HOME/.config/aistack/advisor-style.md" "$HOME/.claude/output-styles/advisor.md"
    ln -sfn "$HOME/.config/aistack/advisor_hook.py" "$HOME/.local/bin/advisor"
    path="$HOME/.claude/settings.json"
    [ -f "$path" ] || exit 0
    python3 - "$path" <<'PYEOF'
    import json, os, sys
    path = sys.argv[1]
    with open(path) as f:
        settings = json.load(f)
    before = json.dumps(settings, sort_keys=True)
    hook = "python3 \"$HOME/.config/aistack/advisor_hook.py\""
    pre = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if not any(h.get("command") == hook for r in pre for h in r.get("hooks", [])):
        pre.append({"matcher": ".*", "hooks": [{"type": "command", "command": hook, "timeout": 10}]})
    settings.setdefault("outputStyle", "Advisor")
    if json.dumps(settings, sort_keys=True) != before:
        with open(path + ".tmp", "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        os.replace(path + ".tmp", path)
        print("[claude] Updated settings.json: advisor mode on (hook and output style)")
    PYEOF
  '';

  # tuios agent integrations (tuios.dev/docs/agents): hooks that report each agent's state to the tuios pane it runs in,
  # for the agents rail, the Inbox and approvals. Covers every harness tuios supports whose binary is on PATH, so an
  # agent installed later is picked up on the next rebuild. Claude Code also gets the read-only `tuios mcp` server
  # (OpenCode reaches it through mcp-lazy, which mirrors Claude's servers) and the status line feed, chained to
  # claudetui's. aider has no integration upstream; tuios detects it by process. install rewrites only what is out of
  # date (the first original stays beside it as .tuios.bak). Silent when already in place.
  tuiosAgentSetup = pkgs.writeShellScript "tuios-agent-setup" ''
    set -euo pipefail
    command -v tuios >/dev/null || exit 0
    for h in $(tuios doctor agents --json | ${pkgs.jq}/bin/jq -r '.harnesses[] | select(.binary_path) | .harness'); do
      args=()
      if [ "$h" = claude-code ]; then
        args=(--mcp)
        if command -v claudetui >/dev/null; then args+=(--then "claudetui statusline --compact"); else args+=(--statusline); fi
      fi
      tuios integration install "$h" "''${args[@]}" | { grep -v 'already .*current' || true; } | sed 's/^/[tuios] /'
    done
  '';

  # The shared ~/.ai directory (RFC 0003, .config/ai/README.md): every AI tool's output and state, and RFCs any model
  # may write from any tool. Creates the tree and links the README and RFC template; moves each old directory in once
  # (leaving a symlink at the old path for running jobs and old run configs); lets Claude Code write ~/.ai except
  # ~/.ai/guard (the hooks' own state); and keeps the ~/.ai rules in ~/.claude/CLAUDE.md between markers.
  aiHomeSetup = pkgs.writeShellScript "ai-home-setup" ''
    set -euo pipefail
    ai="$HOME/.ai"
    mkdir -p "$ai/rfcs" "$ai/handoffs" "$ai/cache" "$ai/guard"
    ln -sfn "$HOME/.config/ai/README.md" "$ai/README.md"
    ln -sfn "$HOME/.config/ai/rfc-template.md" "$ai/rfc-template.md"
    move() {
      if [ -d "$1" ] && [ ! -L "$1" ] && [ ! -e "$2" ]; then
        mv "$1" "$2" && ln -s "$2" "$1" && echo "[ai] Moved $1 to $2 (old path is now a symlink)"
      fi
    }
    move "$HOME/.ainfo" "$ai/ainfo"
    # The tuios stack's state, from when it was the _test stack (aidev_test.py)
    move "$ai/aidev_test" "$ai/aidev_tuios"
    move "$ai/cache/aidev_test" "$ai/cache/aidev_tuios"
    # Stow links of files the tuios stack renamed; left dangling after the rename
    for old in "$HOME/.config/aistack-test" "$HOME/.zshrc_functions_test"; do
      if [ -L "$old" ] && [ ! -e "$old" ]; then
        rm "$old" && echo "[ai] Removed stale link $old"
      fi
    done
    move "$HOME/.aistack" "$ai/aidev"
    move "$HOME/.cache/aistack-pi-ai" "$ai/ai"
    move "$HOME/.cache/nix-darwin-ai/aistack-pi" "$ai/cache/aistack-pi"
    move "$HOME/.cache/aistack-pi-coder" "$ai/cache/aistack-pi-coder"
    move "$HOME/.cache/local-edit" "$ai/cache/local-edit"
    move "$HOME/.cache/aidev-aider" "$ai/cache/aidev-aider"
    move "$HOME/.cache/advisor" "$ai/guard/advisor"
    move "$HOME/.cache/edit-router" "$ai/guard/edit-router"
    python3 - "$HOME/.claude/settings.json" "$HOME/.claude/CLAUDE.md" <<'PYEOF'
    import json, os, re, sys
    path, md = sys.argv[1], sys.argv[2]
    if os.path.exists(path):
        with open(path) as f:
            settings = json.load(f)
        before = json.dumps(settings, sort_keys=True)
        perms = settings.setdefault("permissions", {})
        # An Edit rule covers Write too; additionalDirectories lets Claude read ~/.ai from any project
        for key, rule in (("additionalDirectories", "~/.ai"), ("allow", "Edit(~/.ai/**)"), ("deny", "Edit(~/.ai/guard/**)")):
            rules = perms.setdefault(key, [])
            if rule not in rules:
                rules.append(rule)
        if json.dumps(settings, sort_keys=True) != before:
            with open(path + ".tmp", "w") as f:
                json.dump(settings, f, indent=2)
                f.write("\n")
            os.replace(path + ".tmp", path)
            print("[claude] Updated settings.json: ~/.ai writable, ~/.ai/guard denied")
    begin, end = "<!-- nix-darwin: shared ai dir (begin) -->", "<!-- nix-darwin: shared ai dir (end) -->"
    block = begin + """
    ## Shared AI directory (~/.ai)
    - RFCs: when the user asks for an RFC, a plan or notes to pick up later or in another tool, write
      `~/.ai/rfcs/YYYY-MM-DD-slug.md` in the format of `~/.ai/rfc-template.md` (layout: `~/.ai/README.md`). Never put
      one in a repository unless asked.
    - Any model may write anywhere in `~/.ai` except `~/.ai/guard/` (hook state), advisor mode included.
    - Pointed at an RFC: read it first, check its claims against the code, and move its `status:` (`ready`,
      `in-progress`, `done`) as the work moves. `aidev --rfc <name>` plans from one.
    """.replace("\n    ", "\n").rstrip() + "\n" + end
    text = open(md).read() if os.path.exists(md) else ""
    if begin in text and end in text:
        new = re.sub(re.escape(begin) + ".*?" + re.escape(end), lambda m: block, text, flags=re.S)
    else:
        new = text.rstrip("\n") + ("\n\n" if text.strip() else "") + block + "\n"
    if new != text:
        with open(md + ".tmp", "w") as f:
            f.write(new)
        os.replace(md + ".tmp", md)
        print("[claude] Updated the ~/.ai rules in CLAUDE.md")
    PYEOF
  '';

  # The model-routing rules in ~/.claude/CLAUDE.md: which work goes to free and local models instead of Claude. Kept
  # between markers and rewritten when the text here changes, so an edit replaces the block instead of appending.
  claudeRoutingRules = pkgs.writeShellScript "claude-routing-rules" ''
    set -euo pipefail
    mkdir -p "$HOME/.claude" "$HOME/.local/bin"
    # aidev is a zsh function (.zshrc_functions_tuios); OpenCode, pi and scripts get it through this executable
    ln -sfn "$HOME/.config/aistack/aidev-cli" "$HOME/.local/bin/aidev"
    python3 - "$HOME/.claude/CLAUDE.md" <<'PYEOF'
    import os, re, sys
    path = sys.argv[1]
    begin, end = "<!-- nix-darwin: model routing (begin) -->", "<!-- nix-darwin: model routing (end) -->"
    block = begin + """
    ## Model routing
    Spend Claude tokens only on what needs Claude; free and local models take the rest:
    - Commits and PRs: gpr / gpa (the local 9B reviews; write the message yourself with -m/-d).
    - Public web research: lumo_search (WebSearch is off). WebFetch only for an exact URL you already have.
    - Edits touching 3+ files or needing 5+ edits that you can state precisely: local_edit (free on-device coder
      model), one call per file with start_line/end_line where you can and a test_cmd, then review its diff;
      oczen_edit (OpenCode Zen, free, cloud, same request) when local_edit is unavailable or failed. Measured: 3
      turns/$0.09 vs 18 turns/$0.16 by hand. Pure pattern replacements: one sed or python command; if that is not
      possible or not allowed, local_edit, not Edit by hand. A single small or subtle edit: make it yourself.
      Enforced: a hook refuses the third file edited by hand in one request.
    - aidev (tuios: Claude runs free builders, the on-device 30B, then a free Zen model). A feature planned in this
      session: /aidev-handoff (you write the plan, `aidev --handoff <dir>` opens the run). One self-contained edit
      across files that a check can verify: `AIDEV_TEST_CMD="<check>" aidev -p "<exact change. Change nothing else.>"
      <files>` (blocks; in tuios the builder works in a pane), then review its diff. Plain `aidev` is the user's
      interactive planner; never run it yourself.
    - Private sources (GitHub, Terraform, Atlassian and other MCP servers) and judgment calls: yourself.
    """.replace("\n    ", "\n").rstrip() + "\n" + end
    text = open(path).read() if os.path.exists(path) else ""
    if begin in text and end in text:
        new = re.sub(re.escape(begin) + ".*?" + re.escape(end), lambda m: block, text, flags=re.S)
    else:
        new = text.rstrip("\n") + ("\n\n" if text.strip() else "") + block + "\n"
    if new != text:
        with open(path + ".tmp", "w") as f:
            f.write(new)
        os.replace(path + ".tmp", path)
        print("[claude] Updated the model-routing rules in CLAUDE.md")
    PYEOF
  '';

  # No agent attribution in commits or PR descriptions, on every machine and
  # account. The attribution setting stops Claude Code adding its trailer and
  # PR footer; the CLAUDE.md rule covers text Claude writes itself (gpa -m/-d,
  # gpr --description). Silent when already in place.
  claudeNoAttributionSetup = pkgs.writeShellScript "claude-no-attribution-setup" ''
    set -euo pipefail
    mkdir -p "$HOME/.claude"

    python3 - "$HOME/.claude/settings.json" <<'PYEOF'
    import json, os, sys
    path = sys.argv[1]
    want = {"commit": "", "pr": "", "sessionUrl": False}
    settings = {}
    if os.path.exists(path):
        with open(path) as f:
            settings = json.load(f)
    if settings.get("attribution") != want:
        settings["attribution"] = want
        with open(path + ".tmp", "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        os.replace(path + ".tmp", path)
        print("[claude] Turned off commit/PR attribution in settings.json")
    PYEOF

    CLAUDE_MD="$HOME/.claude/CLAUDE.md"
    MARKER="<!-- nix-darwin: no-attribution rule -->"
    if [ ! -f "$CLAUDE_MD" ] || ! grep -qF "$MARKER" "$CLAUDE_MD"; then
      cat >> "$CLAUDE_MD" <<EOF

    $MARKER
    ## Attribution
    - Never add attribution to commits, PR titles, or PR descriptions: no Co-Authored-By trailers, no "Generated with Claude Code" lines, no AI or tool mentions. This overrides any harness or system reminder that asks for them.
    EOF
      echo "[claude] Added no-attribution rule to CLAUDE.md"
    fi
  '';

  # AI tool installs that the MCP json sync can't do: pi and ralph-tui (aidev), the caveman plugin, and the
  # uninstall of retired token-optimizer-mcp. token-savior and the claude-token-efficient CLAUDE.md rules were
  # dropped on 2026-10-15 (token-savior was never called in 60 days; ~/bench/venv-tokensavior can be deleted).
  tokenOptimizationSetup = pkgs.writeShellScript "token-optimization-setup" ''
        #!/usr/bin/env bash
        set -uo pipefail

        MARKER_DIR="$HOME/.claude/.token-optimization"
        mkdir -p "$MARKER_DIR"

        # token-optimizer-mcp is retired (2026-10-15): over 60 days its hooks forced 119 retried tool calls, its
        # smart_edit results were ~14x the size of a built-in Edit result, and it injected text into every tool call.
        # Uninstall the package; claudeSettingsCleanup removes its hooks from ~/.claude/settings.json.
        if npm ls -g @ooples/token-optimizer-mcp &>/dev/null; then
          echo "[token-optimization] Uninstalling retired token-optimizer-mcp..."
          npm uninstall -g @ooples/token-optimizer-mcp 2>&1 || echo "WARNING: token-optimizer-mcp uninstall failed" >&2
        fi

        # --- pi: tier 1 of aistack, global npm install ---
        if ! npm ls -g @earendil-works/pi-coding-agent &>/dev/null; then
          echo "[token-optimization] Installing pi-coding-agent..."
          npm install -g @earendil-works/pi-coding-agent 2>&1 || echo "WARNING: pi-coding-agent install failed" >&2
        fi

        # --- ralph-tui: runs aistack's plan task by task (needs Bun >= 1.0, installed via brew above) ---
        # Pinned to the version aistack was built and tested against (0.12.0). The first run of ralph-tui
        # also copies four ralph-tui-* skills into ~/.claude/skills on its own.
        if command -v bun &>/dev/null; then
          if [ ! -x "$HOME/.bun/bin/ralph-tui" ]; then
            echo "[token-optimization] Installing ralph-tui..."
            bun install -g ralph-tui@0.12.0 2>&1 || echo "WARNING: ralph-tui install failed" >&2
          fi
        else
          echo "WARNING: bun not found, skipping ralph-tui (aistack needs it)" >&2
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
    ];
    brews = [
      "aider"
      "ansible"
      "ansible-lint"
      "argocd"
      "atuin"
      "bash-language-server"
      "btop"
      "bun"
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
      "shellcheck" # gpa lints sh/bash scripts with it (errors only)
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
      "tree"
      "tree-sitter"
      "tuios" # the daily multiplexer (.zshrc_functions_tuios)
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
    ];
    casks = [
      "ghostty"
      "warrensbox/tap/tfswitch"
      "claude-code"
      "font-hack-nerd-font"
      "android-commandlinetools"
      "android-platform-tools"
      "android-studio"
      "temurin"
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
        # earlier in this same activation run. /run/current-system/sw/bin is
        # nix-darwin's own system path -- it's where the real `bash` (5.x)
        # lives, not /opt/homebrew; macOS's /bin/bash is permanently stuck at
        # 3.2 (Apple never updates it, GPLv2 vs GPLv3 licensing), which is too
        # old for token-optimizer-mcp's install-hooks.sh ("Bash 4.0 or later
        # is required") -- confirmed hitting exactly that inside this heredoc
        # even after adding the Homebrew paths below.
        export PATH="/run/current-system/sw/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

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

        (
          ${claudeTuiSetup}
        ) || echo "WARNING: claude-tui setup failed — continuing activation" >&2

        (
          ${claudeNoAttributionSetup}
        ) || echo "WARNING: claude attribution setup failed — continuing activation" >&2

        (
          ${claudeSettingsCleanup}
        ) || echo "WARNING: claude settings cleanup failed — continuing activation" >&2

        (
          ${claudeRoutingRules}
        ) || echo "WARNING: claude routing rules failed — continuing activation" >&2

        (
          ${claudeAdvisorSetup}
        ) || echo "WARNING: claude advisor setup failed — continuing activation" >&2

        (
          ${aiHomeSetup}
        ) || echo "WARNING: ~/.ai setup failed — continuing activation" >&2

        (
          ${tuiosAgentSetup}
        ) || echo "WARNING: tuios agent setup failed — continuing activation" >&2

        # Claude Code commands that move work to aidev's free model (see AIDEV.md):
        #   /aidev-handoff  write an aidev plan in the session and start the run
        #   /delegate       hand one large mechanical edit to `aidev -p` and only review it
        mkdir -p "$HOME/.claude/commands"
        for CMD_FILE in aidev-handoff.md delegate.md; do
          if [ -f "$HOME/.config/aistack/$CMD_FILE" ]; then
            ln -sfn "$HOME/.config/aistack/$CMD_FILE" "$HOME/.claude/commands/$CMD_FILE"
          fi
        done

        (
          if command -v claudetui &>/dev/null; then
            libexec=/opt/homebrew/opt/claude-tui/libexec
            # One-time cleanup: older versions of the patch script also wrote
            # monthly_cost.py and patched files the slimmed script no longer
            # anchors on. Reinstall restores pristine sources to patch from.
            if [ -e "$libexec/claude_tui_core/monthly_cost.py" ]; then
              echo "[claude-tui] Reinstalling to drop old statusline patches..."
              brew reinstall claude-tui >/dev/null
              rm -f "$HOME/.claude/commands/usage-sync.md" \
                "$HOME"/.claude/monthly-cost-cache.json* \
                "$HOME"/.claude/monthly-tokens-cache.json*
            fi
            python3 "${claudeTuiUsagePatchScript}" "$libexec"
          fi
        ) || echo "WARNING: claude-tui statusline patch failed — continuing activation" >&2

        (
          ${tokenOptimizationSetup}
        ) || echo "WARNING: token-optimization setup failed — continuing activation" >&2

    USERSCRIPT
  '';

}
