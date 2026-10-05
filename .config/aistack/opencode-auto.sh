#!/bin/bash
# Ralph runs `opencode run` without --auto, so every edit/shell permission is auto-rejected and the agent
# prints code instead of writing it. `defaultFlags` puts the flag where opencode rejects it; insert it right
# after `run`. --auto approves anything the user's opencode.json does not explicitly deny.
if [ "$1" = "run" ]; then shift; exec opencode run --auto "$@"; fi
exec opencode "$@"
