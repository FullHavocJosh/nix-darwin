Keep code comments, PR/commit descriptions, ticket text, and Markdown docs
short, technical, and non-redundant. Before finalizing any of those, prefer
calling the `mcp-stack-fullhavoc` MCP tools (`analyze_code_comments`,
`analyze_pr`, `analyze_ticket`, `analyze_commit_messages`) and trim what they
flag: comments restating the adjacent code, commented-out code, filler
phrases, redundant sentences, diff-narrating PR bodies. No comments unless
the WHY is non-obvious.

Never use `--` or em dashes in prose; use `:` or `;`. CLI flags in code are exempt.

Git: commit only with `gpa --auto -m "<subject>" -d "<body>" --json`. Never raw
`git commit`, never `gpc` directly, never commit through `gh` or the GitHub API.
If gpa fails, fix the cause and re-run gpa; never fall back. Branches,
worktrees and PRs only via `gpr`.

Never post from an agent: no `gh pr comment`, `gh issue comment`,
`gh pr review`, `gh pr merge`, no `gh api` comment, review or commit writes.
`gh pr edit` for title/body is allowed.
