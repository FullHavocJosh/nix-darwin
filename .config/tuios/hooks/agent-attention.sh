#!/bin/sh
# This script notifies when agent attention is needed.
# It names the pane and state, never the agent message.
#
# It reads TUIOS_AGENT_STATE, TUIOS_WINDOW_NAME and TUIOS_SESSION_ID.
# For any state other than needs_input or errored it exits 0 and prints nothing.
# Otherwise it prints:
#   "<window> is <state> (<session>) - answer in the tuios Inbox (ctrl+t i)"

# Only notify for needs_input or errored states
if [ "$TUIOS_AGENT_STATE" = "needs_input" ] || [ "$TUIOS_AGENT_STATE" = "errored" ]; then
    # Check if we're in dry run mode
    if [ "${TUIOS_HOOK_DRY_RUN:-0}" = "1" ]; then
        text="$TUIOS_WINDOW_NAME is $TUIOS_AGENT_STATE ($TUIOS_SESSION_ID) - answer in the tuios Inbox (ctrl+t i)"
        printf '%s\n' "$text"
        exit 0
    fi
    
    # Check if we should skip notification
    if [ "${AIDEV_TUIOS_NO_NOTIFY:-0}" = "1" ] || [ "$(uname)" != "Darwin" ]; then
        exit 0
    fi
    
    # Build notification text
    text="$TUIOS_WINDOW_NAME is $TUIOS_AGENT_STATE ($TUIOS_SESSION_ID) - answer in the tuios Inbox (ctrl+t i)"

    # Send notification
    osascript -e 'on run argv' \
        -e 'display notification (item 1 of argv) with title "tuios" sound name "Glass"' \
        -e 'end run' \
        "$text" >/dev/null 2>&1
else
    # For all other states, exit 0 and print nothing
    exit 0
fi

exit 0