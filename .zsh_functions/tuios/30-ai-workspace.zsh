# gpa's manual-fix choices: nvim with $3 and a shell running $4 (aidev) in directory $2. Inside tuios the two windows
# open on the lowest free workspace of this session; elsewhere in a new session $1, attached in a new terminal
# window (_launch_terminal_window, .zshrc_functions_git).
_tuios_ai_edit_workspace() {
  local name="$1" dir="$2" cmd_nvim="$3" cmd_aidev="$4" s ws first
  if [ -n "$TUIOS_ENV" ]; then
    s="$TUIOS_SESSION"
    ws=$(_tuios_cmd list-windows -s "$s" --json | jq -r '([range(1; 10)] - [.windows[].workspace]) | .[0] // empty')
    [ -n "$ws" ] || { echo "tuios: no free workspace in $s for $name" >&2; return 1; }
    _tuios_cmd new-window "ai-$name" -s "$s" --workspace "$ws" --cwd "$dir" --no-focus >/dev/null || return 1
    _tuios_cmd new-window "nvim-$name" -s "$s" --workspace "$ws" --cwd "$dir" >/dev/null || return 1
    [ -n "$cmd_aidev" ] && _tuios_cmd send-text -s "$s" -w "ai-$name" "$cmd_aidev"$'\n' >/dev/null
    [ -n "$cmd_nvim" ] && _tuios_cmd send-text -s "$s" -w "nvim-$name" "$cmd_nvim"$'\n' >/dev/null
    _tuios_cmd select-workspace "$ws" -s "$s" >/dev/null
    return 0
  fi
  _tuios_cmd new "$name" -d --cwd "$dir" >/dev/null || return 1
  first=$(_tuios_cmd list-windows -s "$name" --json | jq -r '.windows[0].window_id')
  _tuios_cmd set-window -s "$name" -w "$first" --name nvim >/dev/null
  _tuios_cmd new-window ai -s "$name" --workspace 1 --cwd "$dir" --no-focus >/dev/null
  [ -n "$cmd_aidev" ] && _tuios_cmd send-text -s "$name" -w ai "$cmd_aidev"$'\n' >/dev/null
  [ -n "$cmd_nvim" ] && _tuios_cmd send-text -s "$name" -w nvim "$cmd_nvim"$'\n' >/dev/null
  _tuios_cmd focus-window nvim -s "$name" >/dev/null
  local attach_script="/tmp/tuios_attach_$$.sh"
  cat >"$attach_script" <<STARTUP
#!/usr/bin/env bash
XDG_CONFIG_HOME="\${XDG_CONFIG_HOME:-\$HOME/.config}" tuios attach '$name'
rm -f '$attach_script'
STARTUP
  chmod +x "$attach_script"
  _launch_terminal_window "$attach_script" "$name"
}

# ai opens the aidev picker (Claude/9B/30B advisor and plan rows); runs inline, in or out of tuios.
ai() {
  python3 "$HOME/.config/aistack-tuios/aidev_pick.py" "$@"
}

# Waits for window $1's visible content to go still (three identical, non-empty reads; about 6s at most) before keys
# are typed into it.

_tuios_wait_pane_stable() {
  local pane_id="$1" prev_content="" cur_content stable_count=0 tries=0
  while [ "$tries" -lt 40 ]; do
    cur_content=$(_tuios_cmd capture-pane -w "$pane_id" 2>/dev/null)
    if [ "$cur_content" = "$prev_content" ] && [ -n "$cur_content" ]; then
      stable_count=$((stable_count + 1))
      [ "$stable_count" -ge 3 ] && return 0
    else
      stable_count=0
    fi
    prev_content="$cur_content"
    sleep 0.15
    tries=$((tries + 1))
  done
}

# prdiff [tuios review flags]: the whole PR of the current branch, as text. tuios review of this pane against the
# merge base with origin's default branch, where ctrl+t v diffs against the branch's upstream.
prdiff() {
  local base mb
  [ -n "$TUIOS_PANE_ID" ] || { echo "prdiff: run it in a tuios pane" >&2; return 1; }
  base=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null) || base=origin/main
  mb=$(git merge-base HEAD "$base") || return 1
  _tuios_cmd review -w "$TUIOS_PANE_ID" --base "$mb" "$@"
}

