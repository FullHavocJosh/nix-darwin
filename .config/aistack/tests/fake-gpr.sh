#!/bin/sh
# Stand-in for `gpr_func --auto ...` in tests: creates .worktrees/$AISTACK_BRANCH in the current repo (no PR, no network),
# records the PR title and body it was given, and prints the same JSON line gpr --auto prints.
git worktree add -q -b "$AISTACK_BRANCH" ".worktrees/$AISTACK_BRANCH" HEAD || exit 1
printf '%s\n---BODY---\n%s\n' "$AISTACK_PR_TITLE" "$AISTACK_PR_BODY" > "$(git rev-parse --git-dir)/fake-gpr-pr.txt"
printf '{"ok":true,"branch":"%s","worktree":"%s/.worktrees/%s","pr_url":"https://example.test/pull/9","pr_number":9}\n' "$AISTACK_BRANCH" "$(pwd)" "$AISTACK_BRANCH"
