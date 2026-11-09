# The session of one project, $1 for directory $2 (nxvim, psvim, hivim, itvim). Skipped on a machine where the
# project is not cloned (~/home-infrastructure is not on the work laptop).
_tuios_project() {
  _tuios_guard || return 1
  local name="$1" dir="$2"
  [ -d "$dir" ] || { echo "tuios: $dir does not exist on this machine, skipping $name" >&2; return 1; }
  cd "$dir" && _tuios_devlayout "$name" "$dir" && _tuios_attach "$name"
}
alias nxvim='_tuios_project nix-darwin ~/nix-darwin'
alias psvim='_tuios_project pscloudops ~/pscloudops'
alias hivim='_tuios_project home-infrastructure ~/home-infrastructure'
alias itvim='_tuios_project Infrastructure-Terrakube ~/Infrastructure-Terrakube'

# hiwt <branch>: a new worktree of the repo on a new branch off its current HEAD, in <repo>/.worktrees/<branch> (where
# gpr puts its worktrees), with a dev session of its own, so in-flight branches never share a working directory.
# Unlike gpr it opens no PR. Run again with the same branch, it reattaches.
_tuios_worktree() {
  _tuios_guard || return 1
  local repo_name="$1" repo_dir="$2" branch="$3"
  [ -n "$branch" ] || { echo "usage: hiwt <branch-name>" >&2; return 1; }
  local wt="$repo_dir/.worktrees/$branch" s="$repo_name-${branch//\//-}"
  if [ ! -d "$wt" ]; then
    git -C "$repo_dir" worktree add -b "$branch" "$wt" HEAD || return 1
  fi
  _tuios_devlayout "$s" "$wt" && _tuios_attach "$s"
}
alias hiwt='_tuios_worktree home-infrastructure ~/home-infrastructure'

# Session $1 whose windows ssh to $2 and work in $3 there: the peer layout uses workspaces 1 and 2 (nvim | zsh on 1, a remote
# shell on 2). Nothing of tuios runs on the remote end. Each command runs through `zsh -ic` there: a plain ssh command is
# not interactive, so the remote .zshrc (and its homebrew PATH) would not load.
_tuios_remote_space_ssh() {
  _tuios_guard || return 1
  local s="$1" host="$2" rdir="$3" first
  local ssh="ssh -t -i ~/.ssh/id_ed25519 $host"
  if ! _tuios_session_exists "$s"; then
    _tuios_cmd new "$s" -d --cwd "$HOME" >/dev/null || return 1
    first=$(_tuios_cmd list-windows -s "$s" --json | jq -r '.windows[0].window_id')
    _tuios_cmd set-window -s "$s" -w "$first" --name nvim >/dev/null
    _tuios_cmd send-text -s "$s" -w nvim "$ssh \"zsh -ic 'cd $rdir && nvim'\""$'\n' >/dev/null
    _tuios_cmd new-window zsh -s "$s" --workspace 1 --cwd "$HOME" --no-focus >/dev/null
    _tuios_cmd send-text -s "$s" -w zsh "$ssh \"zsh -ic 'cd $rdir && git status; exec zsh -l'\""$'\n' >/dev/null
    _tuios_cmd new-window ai -s "$s" --workspace 2 --cwd "$HOME" --no-focus >/dev/null
    _tuios_cmd send-text -s "$s" -w ai "$ssh \"zsh -ic 'cd $rdir; exec zsh -l'\""$'\n' >/dev/null
    _tuios_cmd focus-window nvim -s "$s" >/dev/null
  fi
  _tuios_attach "$s"
}
alias mmdev_ssh='_tuios_remote_space_ssh macmini havoc@macminim1.rollet.family ~'
alias himmdev_ssh='_tuios_remote_space_ssh macmini-home-infrastructure havoc@macminim1.rollet.family ~/home-infrastructure'
alias nxmmdev_ssh='_tuios_remote_space_ssh macmini-nix-darwin havoc@macminim1.rollet.family ~/nix-darwin'

# The foreground program of the terminal $1 (a window's tty, from list-windows): the process ps marks "+".
_tuios_fg() {
  ps -o stat=,comm= -t "${1#/dev/}" 2>/dev/null | awk '$1 ~ /\+/ { sub(".*/", "", $2); sub("^-", "", $2); print $2; exit }'
}

# Points this session's dev windows at $1: gpr passes its new worktree, pr-merged-reset the repo root. nvim gets
# `:cd $1 | Neotree git_status` (open buffers survive), zsh gets `cd $1`. A window is typed into
# only when the program it is named after is in its foreground, so a busy pane or a bare shell never gets keystrokes
# meant for something else.
_tuios_sync_dev_panes() {
  local dir="$1" s="$TUIOS_SESSION" name wid tty
  [ -n "$s" ] || return 0
  _tuios_cmd list-windows -s "$s" --json 2>/dev/null |
    jq -r '.windows[] | select(.custom_name == "nvim" or .custom_name == "zsh")
      | "\(.custom_name) \(.window_id) \(.tty)"' |
    while read -r name wid tty; do
      [ "$wid" = "$TUIOS_PANE_ID" ] && continue
      case "$name" in
        nvim)
          [ "$(_tuios_fg "$tty")" = nvim ] || continue
          # Two escs: one leaves insert mode or a prompt, the second closes a float over it.
          _tuios_cmd send-keys -s "$s" -w "$wid" esc >/dev/null 2>&1
          _tuios_cmd send-keys -s "$s" -w "$wid" esc >/dev/null 2>&1
          _tuios_wait_pane_stable "$wid"
          _tuios_cmd send-text -s "$s" -w "$wid" ":cd $dir | Neotree git_status" >/dev/null 2>&1
          _tuios_cmd send-keys -s "$s" -w "$wid" enter >/dev/null 2>&1
          ;;
        zsh)
          [ "$(_tuios_fg "$tty")" = zsh ] || continue
          _tuios_cmd send-text -s "$s" -w "$wid" "cd $dir"$'\n' >/dev/null 2>&1
          ;;
      esac
    done
}

