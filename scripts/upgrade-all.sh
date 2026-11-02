#!/usr/bin/env bash
# This script upgrades various package managers and tools
# It reads from stdin (load-bearing: the caller feeds this over a heredoc)
# It does NOT modify PATH (caller sets it)

STATUS_FILE=${UPGRADE_STATUS_FILE:-$HOME/.cache/darwin-upgrade-status}
mkdir -p "$(dirname "$STATUS_FILE")"

FAILED=()

step() {
    local name="$1"
    shift

    # Check if the first command exists
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Skipping $name (command not found)" >&2
        return 0
    fi

    # Run the command with stdin from /dev/null (load-bearing: the caller feeds this over a heredoc)
    if ! "$@" < /dev/null; then
        FAILED+=("$name")
        echo "FAILED: $name" >&2
    fi
}

step brew brew upgrade --greedy
step npm npm update -g
step uv uv tool upgrade --all
step pipx pipx upgrade-all
step rustup rustup update

# Check results
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "ok" > "$STATUS_FILE"
    echo "All package upgrades succeeded"
    exit 0
else
    echo "failed: ${FAILED[*]}" > "$STATUS_FILE"
    echo "================================================" >&2
    echo "UPGRADE FAILURES: ${FAILED[*]}" >&2
    echo "================================================" >&2
    exit 1
fi