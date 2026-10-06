#!/bin/bash
# Ralph always passes --dangerously-skip-permissions to claude. For the review tier drop it and allow only
# reading, running the project's unit tests, and writing the report under $AISTACK_REVIEWS_DIR (outside the
# repository, in ~/.aistack/<project>/reviews). Ralph itself runs from the aistack state dir, so cd to the
# directory the code lives in first. `Edit(//abs/**)` is Claude Code's absolute-path rule syntax.
if [ -n "$AISTACK_WORKDIR" ]; then cd "$AISTACK_WORKDIR" || exit 1; fi
args=()
for a in "$@"; do
  [ "$a" = "--dangerously-skip-permissions" ] && continue
  args+=("$a")
done
# Claude is billed: cap what the review can spend and how hard it thinks (AISTACK_CLAUDE_BUDGET_REVIEW in USD,
# AISTACK_CLAUDE_EFFORT). One review call covers the whole run; read-only git commands let it read the diff instead of
# crawling files.
limits=(--max-budget-usd "${AISTACK_CLAUDE_BUDGET_REVIEW:-1.5}" --effort "${AISTACK_CLAUDE_EFFORT:-medium}")
tools=("Read" "Grep" "Glob" "Bash(python3 -m unittest:*)" "Bash(ls:*)" "Bash(cat:*)" "Bash(git diff:*)" "Bash(git status:*)" "Bash(git log:*)")
if [ -n "$AISTACK_REVIEWS_DIR" ]; then
  exec claude "${args[@]}" "${limits[@]}" --add-dir "$AISTACK_REVIEWS_DIR" --allowedTools "${tools[@]}" "Edit(/$AISTACK_REVIEWS_DIR/**)"
fi
exec claude "${args[@]}" "${limits[@]}" --allowedTools "${tools[@]}"
