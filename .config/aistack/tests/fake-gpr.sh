#!/bin/sh
# Stand-in for gpr_func in tests: creates .worktrees/$AISTACK_BRANCH in the current repo (no PR, no network).
git worktree add -q -b "$AISTACK_BRANCH" ".worktrees/$AISTACK_BRANCH" HEAD
