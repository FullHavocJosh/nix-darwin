#!/bin/bash
# Ralph runs `opencode run` without --auto, so every edit/shell permission is auto-rejected and the agent
# prints code instead of writing it. `defaultFlags` puts the flag where opencode rejects it; insert it right
# after `run`. --auto approves anything the user's opencode.json does not explicitly deny.
# Ralph runs from the aistack state dir, so cd to the directory the code lives in first.
if [ -n "$AISTACK_WORKDIR" ]; then cd "$AISTACK_WORKDIR" || exit 1; fi
if [ "$1" = "run" ]; then shift; exec opencode run --auto "$@"; fi
exec opencode "$@"
