#!/bin/bash
# Ralph runs from the aistack state dir (it keeps its session files in <cwd>/.ralph-tui, which must not be the
# repository); the agent has to work in the directory the code lives in.
if [ -n "$AISTACK_WORKDIR" ]; then cd "$AISTACK_WORKDIR" || exit 1; fi
# Claude is billed: cap what one call can spend and how hard it thinks. Override with AISTACK_CLAUDE_BUDGET_WORK (USD)
# and AISTACK_CLAUDE_EFFORT (low|medium|high|xhigh|max). --max-budget-usd only applies to print mode, which Ralph uses.
#
# Model and effort come from AISTACK_CLAUDE_MODEL / AISTACK_CLAUDE_EFFORT, which nix-darwin sets per profile
# (nix-modules/macos/work.nix and personal.nix); aistack_func writes the same model into Ralph's agent options.
exec claude "$@" --model "${AISTACK_CLAUDE_MODEL:-sonnet}" --max-budget-usd "${AISTACK_CLAUDE_BUDGET_WORK:-3}" --effort "${AISTACK_CLAUDE_EFFORT:-medium}"
