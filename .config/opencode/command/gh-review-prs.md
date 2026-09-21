---
description: Fetch open PRs pending your review, cross-reference #plat-code-review, and produce a structured AI analysis of each one.
agent: build
---

# PR Review Dashboard

Fetch all open pull requests pending your review, cross-reference against #plat-code-review Slack channel to confirm the author is actively seeking approval, then provide a structured AI analysis of each one.

## Steps

1. Run the following shell command and capture the output:

   ```
   gh search prs --review-requested=@me --state=open --limit=20 --json number,title,repository,url,author,createdAt,updatedAt 2>&1
   ```

2. Parse the JSON output to get the list of PRs. For each PR, extract:
   - `repository` (in `nameWithOwner` format)
   - `number`
   - `title`
   - `url`
   - `author.login`
   - `createdAt` and `updatedAt`

   For each PR, fetch its timeline to find when it was marked ready for review:

   ```
   gh api repos/{owner}/{repo}/issues/{number}/timeline --paginate --jq '[.[] | select(.event == "ready_for_review")] | last | .created_at' 2>&1
   ```
   - If a `ready_for_review` event is found, use that timestamp as the PR's "active since" date.
   - If no `ready_for_review` event exists (was never a draft), fall back to `createdAt`.

   **Filter out any PRs where the "active since" date is more than 14 days ago** (relative to today). If any were dropped, note at the end: "X PR(s) marked ready for review more than 2 weeks ago were hidden."

   Use the "active since" date (not `createdAt`) when displaying age in days.

3. **Slack cross-reference:** Check if a Slack MCP tool is available to read `#plat-code-review`.
   - If a Slack MCP tool IS available: use it to fetch recent messages from `#plat-code-review` (last 7 days), cross-reference each PR by matching the PR URL or number against messages, then **keep only PRs that appear in the channel** — drop the rest silently. Note at the end: "X PR(s) not posted in #plat-code-review were hidden."
   - If NO Slack MCP is available: say "I don't have Slack access in this session. Paste recent messages from #plat-code-review and I'll filter to only those PRs, or say 'skip' to see all." If the user pastes Slack content, apply the same filter — **keep only PRs whose URL or number appears in the paste**, drop the rest. If the user says 'skip', show all PRs with ❓ status.

4. Display a numbered list of the remaining PRs (those actively posted in #plat-code-review) with: number, repo, title, author, and age in days. Ask the user which PR(s) they want to review — they can say a number, a list like `1,3`, or `all`.

5. For each selected PR, use the GitHub MCP tools to gather in parallel:
   - `github_pr_details` — status, reviewers, CI checks
   - `github_pr_changes` with format `patch` — the actual diff
   - `github_pr_comments_get` — existing review comments and discussions

   (Tool names are exposed with the `github_github_*` prefix in opencode; use whichever GitHub MCP tools are actually available in this session.)

6. Analyze the gathered data and produce a structured review for each PR using this format:

---

### PR #[number] — [title]

**Repo:** [owner/repo] | **Author:** [author] | **Age:** [N days]
**Slack:** ✅ Posted in #plat-code-review / ⚠️ Not posted / ❓ Unknown
**URL:** [url]

#### Summary

2-3 sentence plain-English description of what this PR does and why.

#### Risk Assessment

- **Risk level:** Low / Medium / High
- Key risk factors (e.g., large diff, touching critical paths, missing tests, CI failures)

#### What Changed

Bullet list of the significant changes — files or areas touched, not a line-by-line diff recap.

#### Open Questions / Clarifications Needed

Numbered list of specific things to ask the author before approving. Focus on:

- Ambiguous logic or missing context
- Missing tests for edge cases
- Breaking changes that aren't documented
- Security or performance concerns

#### Recommendation

One of: **Approve** / **Request Changes** / **Needs Discussion** — with a one-sentence justification.

---

7. After all selected PRs are reviewed, ask: "Would you like to open any of these in the browser? (enter numbers or 'no')" — if yes, run `gh pr view --web [number] --repo [owner/repo]` for each selected one.
