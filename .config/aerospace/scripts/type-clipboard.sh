#!/bin/sh
# Types the current clipboard contents out as simulated keystrokes, for contexts
# that forward keyboard input but not clipboard sync (RDP, AWS Fleet Manager,
# etc.). Bound to cmd-ctrl-v in aerospace.toml.
#
# The delay is required, not cosmetic: this fires on the key-DOWN event, so the
# physical cmd/ctrl keys used to trigger the binding are often still held down
# for a couple hundred ms afterward. Typing a character during that window
# combines with the still-held modifiers and can fire an unrelated system
# shortcut -- observed in practice: an "L" landing as ctrl-cmd-L, which locks the
# screen. The delay gives fingers time to fully release before anything types.
osascript -e '
delay 0.4
tell application "System Events" to keystroke (the clipboard as text)
'
