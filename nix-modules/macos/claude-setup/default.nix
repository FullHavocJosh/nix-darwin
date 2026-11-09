# Claude Code, tuios and ~/.ai setup that runs at the end of every activation. Each setup script is a
# shell file in scripts/, built with writeShellScript. post-activation/ holds the pieces of the
# user-level activation script that runs them, joined in name order. Returns the script text;
# packages-tui.nix sets it as postActivation, because a module of its own would sort after the
# other modules' postActivation text.
{
  pkgs,
  lib,
  username,
}:
let
  fragments = import ../lib/fragments.nix { inherit lib; };

  # See claude-tui-usage-patch.py: single labeled usage bar on the compact
  # statusline, no model name.
  claudeTuiUsagePatchScript = pkgs.writeText "claude-tui-usage-patch.py" (
    builtins.readFile ../claude-tui-usage-patch.py
  );

  claudeTuiSetup = pkgs.writeShellScript "claude-tui-setup" (
    fragments.file ./scripts/claude-tui-setup.sh { }
  );

  # Keeps ~/.claude/settings.json free of hooks from retired tools, routes web search through Lumo, and enforces the
  # edit routing (edit_router_hook.py; CLAUDE_EDIT_ROUTER=off turns it off for a session):
  #   - removes token-optimizer-mcp's hooks and claude-tui's hooks (see tokenOptimizationSetup / claudeTuiSetup)
  #   - denies the built-in WebSearch; the lumo MCP server (.config/lumo/lumo_mcp.py) answers web questions instead.
  #     WebFetch stays allowed for reading one exact page.
  # Silent when already in place.
  claudeSettingsCleanup = pkgs.writeShellScript "claude-settings-cleanup" (
    fragments.file ./scripts/claude-settings-cleanup.sh { }
  );

  # Advisor mode (.config/aistack/advisor_hook.py, on by default in every session): Claude reads, searches and reviews,
  # and hands the user every change as a command or diff with an explanation, to run themselves as `! <command>`.
  #   - registers advisor_hook.py as a PreToolUse hook on every tool
  #   - links the Advisor output style (.config/aistack/advisor-style.md) and selects it when no style is set
  #   - links ~/.local/bin/advisor, the per-session switch: `! advisor off|on|status`
  # CLAUDE_ADVISOR=off claude starts a session without it. Silent when already in place.
  claudeAdvisorSetup = pkgs.writeShellScript "claude-advisor-setup" (
    fragments.file ./scripts/claude-advisor-setup.sh { }
  );

  # tuios agent integrations (tuios.dev/docs/agents): hooks that report each agent's state to the tuios pane it runs in,
  # for the agents rail, the Inbox and approvals. Covers every harness tuios supports whose binary is on PATH, so an
  # agent installed later is picked up on the next rebuild. Claude Code also gets the read-only `tuios mcp` server
  # (OpenCode reaches it through mcp-lazy, which mirrors Claude's servers) and the status line feed, chained to
  # claudetui's. aider has no integration upstream; tuios detects it by process. install rewrites only what is out of
  # date (the first original stays beside it as .tuios.bak). Silent when already in place.
  tuiosAgentSetup = pkgs.writeShellScript "tuios-agent-setup" (
    fragments.file ./scripts/tuios-agent-setup.sh {
      jq = "${pkgs.jq}";
    }
  );

  # The shared ~/.ai directory (RFC 0003, .config/ai/README.md): every AI tool's output and state, and RFCs any model
  # may write from any tool. Creates the tree and links the README and RFC template; moves each old directory in once
  # (leaving a symlink at the old path for running jobs and old run configs); lets Claude Code write ~/.ai except
  # ~/.ai/guard (the hooks' own state); and keeps the ~/.ai rules in ~/.claude/CLAUDE.md between markers.
  aiHomeSetup = pkgs.writeShellScript "ai-home-setup" (fragments.file ./scripts/ai-home-setup.sh { });

  # The model-routing rules in ~/.claude/CLAUDE.md: which work goes to free and local models instead of Claude. Kept
  # between markers and rewritten when the text here changes, so an edit replaces the block instead of appending.
  claudeRoutingRules = pkgs.writeShellScript "claude-routing-rules" (
    fragments.file ./scripts/claude-routing-rules.sh { }
  );

  # No agent attribution in commits or PR descriptions, on every machine and
  # account. The attribution setting stops Claude Code adding its trailer and
  # PR footer; the CLAUDE.md rule covers text Claude writes itself (gpa -m/-d,
  # gpr --description). Silent when already in place.
  claudeNoAttributionSetup = pkgs.writeShellScript "claude-no-attribution-setup" (
    fragments.file ./scripts/claude-no-attribution-setup.sh { }
  );

  # AI tool installs that the MCP json sync can't do: pi (ai, ainfo and aidev's panes), the caveman plugin, and the
  # uninstall of retired token-optimizer-mcp. token-savior and the claude-token-efficient CLAUDE.md rules were
  # dropped on 2026-10-15 (token-savior was never called in 60 days; ~/bench/venv-tokensavior can be deleted).
  tokenOptimizationSetup = pkgs.writeShellScript "token-optimization-setup" (
    fragments.file ./scripts/token-optimization-setup.sh { }
  );
in
fragments.dir ./post-activation {
  aiHomeSetup = "${aiHomeSetup}";
  claudeAdvisorSetup = "${claudeAdvisorSetup}";
  claudeNoAttributionSetup = "${claudeNoAttributionSetup}";
  claudeRoutingRules = "${claudeRoutingRules}";
  claudeSettingsCleanup = "${claudeSettingsCleanup}";
  claudeTuiSetup = "${claudeTuiSetup}";
  claudeTuiUsagePatchScript = "${claudeTuiUsagePatchScript}";
  gnused = "${pkgs.gnused}";
  tokenOptimizationSetup = "${tokenOptimizationSetup}";
  tuiosAgentSetup = "${tuiosAgentSetup}";
  upgradeAll = "${../../../scripts/upgrade-all.sh}";
  usernameQuoted = "\"${username}\"";
}
