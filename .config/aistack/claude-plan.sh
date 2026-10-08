#!/bin/bash
# aidev's planning call: Claude Code writes the plan from the research the local model passes in (ralph_plan in
# ralph_mcp.py calls this with `-p <prompt>`). It is billed, so the call is kept as small as it can be:
#   --tools                   only Read, Grep and Glob exist for the model (no Bash, Edit, Write, web or agents)
#   --strict-mcp-config       no MCP servers (none are passed), so no tool schemas from them are loaded
#   --disable-slash-commands  no skills
#   --max-budget-usd          hard cap for the one call (AISTACK_CLAUDE_BUDGET_PLAN, USD)
#   --restricted              ignores the user, project and local settings files, so none of this machine's Claude Code
#                             hooks and plugins run in the call. They did two kinds of damage here, measured on
#                             2026-10-08: a hook refused the built-in Glob and told Claude to use an MCP tool that
#                             this call does not have (every lookup cost a wasted turn), and session-start hooks
#                             added about 8,000 tokens to the prompt (10,374 -> 2,191 tokens written per call).
#                             It also confines Read/Grep/Glob to the project directory. The OAuth login still works.
# --bare would strip more, but it refuses the OAuth login this machine uses, so it is not used.
# Model and effort come from AISTACK_CLAUDE_MODEL / AISTACK_CLAUDE_EFFORT, like claude-work.sh and claude-review.sh.
if [ -n "$AISTACK_WORKDIR" ]; then cd "$AISTACK_WORKDIR" || exit 1; fi
exec claude "$@" --model "${AISTACK_CLAUDE_MODEL:-sonnet}" --max-budget-usd "${AISTACK_CLAUDE_BUDGET_PLAN:-1.5}" \
  --effort "${AISTACK_CLAUDE_EFFORT:-medium}" --tools "Read,Grep,Glob" --allowedTools "Read" "Grep" "Glob" \
  --strict-mcp-config --disable-slash-commands --restricted
