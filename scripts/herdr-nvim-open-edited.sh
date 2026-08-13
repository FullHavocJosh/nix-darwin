#!/bin/sh
# Claude Code PostToolUse hook (Edit|Write|MultiEdit|NotebookEdit).
#
# Mirrors edited files into the sibling "nvim" pane of the same herdr tab
# (see .zshrc_aliases _herdr_populate_panes), the way tuicr already surfaces
# them for review. `:edit` only swaps the current window's buffer -- it never
# closes other tabs -- and nvim's default 'hidden' is on, so it doesn't matter
# whether the target buffer already has unsaved changes.
set -eu

[ "${HERDR_ENV:-}" = "1" ] || exit 0
[ -n "${HERDR_WORKSPACE_ID:-}" ] || exit 0
[ -n "${HERDR_TAB_ID:-}" ] || exit 0
command -v herdr >/dev/null 2>&1 || exit 0
command -v jq >/dev/null 2>&1 || exit 0

hook_input="$(cat)"

file_path="$(printf '%s' "$hook_input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')"
[ -n "$file_path" ] || exit 0

pane_id="$(herdr pane list --workspace "$HERDR_WORKSPACE_ID" 2>/dev/null \
  | jq -r --arg tab "$HERDR_TAB_ID" \
    '.result.panes[]? | select(.label=="nvim" and .tab_id==$tab) | .pane_id' \
  | head -n1)"
[ -n "$pane_id" ] || exit 0

# Single-quoted vimscript string literal: double up embedded single quotes.
escaped_path=$(printf '%s' "$file_path" | sed "s/'/''/g")

# `herdr pane run` (text+Enter in one call) reliably races with nvim here --
# the colon command lands as literal inserted text instead of executing. The
# three-step send-keys/send-text/send-keys sequence used elsewhere for tuicr
# (_tuicr_restart in .zshrc_aliases) does not have that problem, so match it.
herdr pane send-keys "$pane_id" esc >/dev/null 2>&1 || true
herdr pane send-text "$pane_id" ":execute 'edit ' . fnameescape('${escaped_path}')" >/dev/null 2>&1 || true
herdr pane send-keys "$pane_id" enter >/dev/null 2>&1 || true

exit 0
