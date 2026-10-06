#!/bin/bash
# Ralph runs from the aistack state dir (it keeps its session files in <cwd>/.ralph-tui, which must not be the
# repository); the agent has to work in the directory the code lives in.
if [ -n "$AISTACK_WORKDIR" ]; then cd "$AISTACK_WORKDIR" || exit 1; fi
exec claude "$@"
