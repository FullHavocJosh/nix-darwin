Keep code comments, PR/commit descriptions, ticket text, and Markdown docs
short, technical, and non-redundant. Before finalizing any of those, prefer
calling the `mcp-stack-fullhavoc` MCP tools (`analyze_code_comments`,
`analyze_pr`, `analyze_ticket`, `analyze_commit_messages`) and trim what they
flag: comments restating the adjacent code, commented-out code, filler
phrases, redundant sentences, diff-narrating PR bodies. No comments unless
the WHY is non-obvious.
