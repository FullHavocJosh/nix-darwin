#!/bin/bash
# aidev's URL fetch: a small Claude Code call reads the URLs the user put in the request (Jira and Confluence through the
# claude.ai Atlassian connector, GitHub and Terraform through their MCP servers, anything else through WebFetch) and
# returns their content as JSON. ralph_mcp.py (resolve_urls) calls this with `-p <prompt>`. It is billed, so it is small:
#   --model haiku             reading and copying out a page needs no planner (AISTACK_CLAUDE_FETCH_MODEL overrides)
#   --tools WebFetch,ToolSearch
#                             the only built-in tools. ToolSearch keeps MCP tool schemas deferred: without it every
#                             server's schemas were loaded and one fetch cost 0.30 USD instead of 0.03 (2026-10-14).
#   --setting-sources ""      no user, project or local settings, so no hooks, plugins or permission rules run here;
#                             the allowlist below is the whole permission set. Unlike --restricted and
#                             --strict-mcp-config (claude-plan.sh), this keeps the claude.ai connectors loaded.
#   --allowedTools            read-only tools only. In -p mode anything not listed is denied, so the Atlassian and
#                             GitHub write tools (comment, edit, transition, pr_create, pr_approve) cannot run.
#   --max-budget-usd          hard cap for the one call (AISTACK_CLAUDE_BUDGET_FETCH, USD)
if [ -n "$AISTACK_WORKDIR" ]; then cd "$AISTACK_WORKDIR" || exit 1; fi
A=mcp__claude_ai_Atlassian_Rovo
G=mcp__github
exec claude "$@" --model "${AISTACK_CLAUDE_FETCH_MODEL:-haiku}" --max-budget-usd "${AISTACK_CLAUDE_BUDGET_FETCH:-0.3}" \
  --effort low --tools "WebFetch,ToolSearch" --setting-sources "" --disable-slash-commands \
  --allowedTools "ToolSearch" "WebFetch" \
  "${A}__getAccessibleAtlassianResources" "${A}__fetch" "${A}__search" "${A}__getJiraIssue" \
  "${A}__getJiraIssueRemoteIssueLinks" "${A}__searchJiraIssuesUsingJql" "${A}__getConfluencePage" \
  "${A}__getConfluencePageFooterComments" "${A}__getConfluencePageInlineComments" "${A}__getConfluenceCommentChildren" \
  "${A}__getConfluencePageDescendants" "${A}__searchConfluenceUsingCql" \
  "${G}__github_file_get" "${G}__github_pr_details" "${G}__github_pr_changes" "${G}__github_pr_comments_get" \
  "${G}__github_pr_list" "${G}__github_issues_list" "${G}__github_branch_list" "${G}__github_repos_list" \
  "mcp__terraform"
