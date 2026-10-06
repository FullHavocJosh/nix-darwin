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
if [ -n "$AISTACK_REVIEWS_DIR" ]; then
  exec claude "${args[@]}" --add-dir "$AISTACK_REVIEWS_DIR" \
    --allowedTools "Read" "Grep" "Glob" "Edit(/$AISTACK_REVIEWS_DIR/**)" "Bash(python3 -m unittest:*)" "Bash(ls:*)" "Bash(cat:*)"
fi
exec claude "${args[@]}" \
  --allowedTools "Read" "Grep" "Glob" "Bash(python3 -m unittest:*)" "Bash(ls:*)" "Bash(cat:*)"
