    (
      @claudeTuiSetup@
    ) || echo "WARNING: claude-tui setup failed — continuing activation" >&2

    (
      @claudeNoAttributionSetup@
    ) || echo "WARNING: claude attribution setup failed — continuing activation" >&2

    (
      @claudeSettingsCleanup@
    ) || echo "WARNING: claude settings cleanup failed — continuing activation" >&2

    (
      @claudeRoutingRules@
    ) || echo "WARNING: claude routing rules failed — continuing activation" >&2

    (
      @claudeAdvisorSetup@
    ) || echo "WARNING: claude advisor setup failed — continuing activation" >&2

    (
      @aiHomeSetup@
    ) || echo "WARNING: ~/.ai setup failed — continuing activation" >&2

    (
      @tuiosAgentSetup@
    ) || echo "WARNING: tuios agent setup failed — continuing activation" >&2

