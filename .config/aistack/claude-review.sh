#!/bin/bash
# Ralph always passes --dangerously-skip-permissions to claude. For the review tier drop it and allow only
# reading, running the project's unit tests, and writing the report under .aistack/reviews/.
args=()
for a in "$@"; do
  [ "$a" = "--dangerously-skip-permissions" ] && continue
  args+=("$a")
done
exec claude "${args[@]}" \
  --allowedTools "Read" "Grep" "Glob" "Edit(.aistack/reviews/**)" "Bash(python3 -m unittest:*)" "Bash(ls:*)" "Bash(cat:*)"
