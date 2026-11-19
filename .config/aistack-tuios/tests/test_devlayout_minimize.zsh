#!/usr/bin/env zsh

# Test script for _tuios_devlayout: nvim and pick open minimized, zsh stays visible and takes the focus.
# Shadows the tuios calls to log them without touching a real session.

tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/devlayout.XXXXXX")
log_file="$tmpdir/calls.log"

for f in "${0:A:h}"/../../../.zsh_functions/tuios/*.zsh; do source "$f"; done

_tuios_daemon_up() { return 0; }
_tuios_session_exists() { return 1; }
_tuios_cmd() {
    echo "$*" >> "$log_file"
    if [[ "$1" == "list-windows" ]]; then
        echo '{"windows":[{"window_id":"w1"}]}'
    fi
    return 0
}

failures=0
check() {
    local name="$1" condition="$2"
    if eval "$condition"; then
        echo "PASS $name"
    else
        echo "FAIL $name"
        ((failures++))
    fi
}

_tuios_devlayout t /tmp

check "nvim minimized" "grep -q -- 'set-window -s t -w nvim --minimize' \"$log_file\""
check "pick minimized" "grep -q -- 'set-window -s t -w pick --minimize' \"$log_file\""
check "zsh not minimized" "! grep -q -- '-w zsh --minimize' \"$log_file\""
check "focus zsh last" "[ \"\$(tail -n1 \"$log_file\")\" = 'focus-window zsh -s t' ]"

rm -f "$log_file"
rmdir "$tmpdir"

if [ $failures -gt 0 ]; then
    exit 1
else
    exit 0
fi
