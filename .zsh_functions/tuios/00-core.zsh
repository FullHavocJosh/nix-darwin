# The daily terminal and AI stack, on tuios.
#
#   dev                  reattach the daemon's sessions; with none, create nix-darwin, terraform-infrastructure and
#                        home-infrastructure where cloned. Layout: workspace 1 holds nvim, aidev's Claude, Lumo
#                        and the builders. Where ~/ai-info exists, dev also ensures an ai-info session and a manage
#                        window (never duplicated), on the other Mac too through dev --detached
#   devim [name]         the same layout for the current directory, always a new session
#   nxvim, psvim, hivim, itvim   the session of one project (skipped where it is not cloned)
#   hiwt <branch>        a new home-infrastructure worktree and branch, with a session of its own
#   peerdev, nxpeer, hipeer, mmdev, himmdev, nxmmdev      sessions of the other Mac opened through the tuios host link
#   aidev [task]         Claude Code as backbone, Lumo for web lookups, a free builder, mailing each other, as extra
#                        workspaces of the current tuios session (outside tuios: session <repo>;
#                        .config/aistack-tuios/aidev_tuios.py)
#   aidev --resume, aidev_status
#   aidev -p "<change>" [files]   one edit by a free builder (a pane on a free workspace), AIDEV_TEST_CMD checked
#   aidev --handoff <dir>         a run for a plan another session wrote; aidev --rfc <name> plans from an RFC
#   aidev --direct [words]        a free builder, interactive, in this terminal
#   ai_tuios [-c] [msg]  one Claude Code pane in session <dir>
#
# Every dev layout and every ai edit session also has a bare zsh window (named zsh, workspace 1).
#
# gpr points this session's nvim and zsh windows at a new worktree (_tuios_sync_dev_panes), and gpa's manual-fix
# choices open nvim and aidev in a free workspace (_tuios_ai_edit_workspace).
#
# Review: ctrl+t v opens tuios's review view of the focused pane's changes, against the branch's upstream (a pushed gpr
# branch shows only unpushed and uncommitted work). c notes a line, C a hunk, S sends the notes to the pane's agent.
# prdiff prints the whole PR's diff against origin's default branch.
#
# Keys (.config/tuios/config.toml): ctrl+t is tuios's prefix. ctrl+1..9 workspaces, ctrl+shift+j/k next/previous
# session, ctrl+shift+p go to an agent, session or pane, ctrl+shift+h sidebar, ctrl+h/l previous/next window, ctrl+j/k
# next/previous agent in every session; ctrl+t i agents and the Inbox, ctrl+t g lazygit, ctrl+t s scratch terminal,
# ctrl+t n/w/W new window/close window/close session, ctrl+t hjkl focus, ctrl+t space workspace prefix, ctrl+t q
# detach, ctrl+t ctrl+t sends ctrl+t to the pane. Without the prefix: ctrl+tab/ctrl+shift+tab cycle windows,
# ctrl+shift+arrows move focus, ctrl+shift+1..9 move the pane to a workspace.
# tuios is ctrl only; alt belongs to aerospace.

# tuios with the stowed config (~/.config/tuios; on macOS tuios otherwise reads ~/Library/Application
# Support/tuios).
_tuios_cmd() {
  (
    XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}" command tuios "$@"
  )
}

_tuios_guard() {
  command -v tuios >/dev/null || { echo "tuios is not installed (darwin-rebuild installs it through brew)." >&2; return 1; }
}

_tuios_session_exists() {
  _tuios_cmd ls --json 2>/dev/null | jq -e --arg n "$1" '.[]? | select(.name==$n)' >/dev/null 2>&1
}

# Inside tuios, switch this client to the session instead of nesting a second client in a pane.
_tuios_attach() {
  if [ -n "$TUIOS_ENV" ]; then
    _tuios_cmd switch-session "$1"
  else
    _tuios_cmd attach "$1"
  fi
}

# Starts the daemon when it is down. `tuios ls` never starts it, so after a reboot every session looked missing, and
# the first `tuios new` started the daemon, which restored the saved sessions, and then failed with "session already
# exists". start-server exits 1 when the daemon already runs; the wait covers the sessions it restores at start.
_tuios_daemon_up() {
  local i=0
  _tuios_cmd ls --json >/dev/null 2>&1 && return 0
  _tuios_cmd start-server >/dev/null 2>&1
  until _tuios_cmd ls --json >/dev/null 2>&1 || [ "$i" -ge 25 ]; do
    sleep 0.2
    i=$((i + 1))
  done
}

