# tuios restores a session's window names, directories and history, but each window gets a fresh shell. Types nvim
# into session $1's nvim window when a shell is in its foreground (after a restore, or after you quit nvim there).
# A shell still drawing its prompt shows starship in the foreground, so wait up to 3s for that to settle.
_tuios_restore_nvim() {
  local s="$1" wid tty fg i
  _tuios_cmd list-windows -s "$s" --json 2>/dev/null |
    jq -r '.windows[] | select(.custom_name == "nvim") | "\(.window_id) \(.tty)"' |
    while read -r wid tty; do
      i=0
      fg=$(_tuios_fg "$tty")
      while { [ -z "$fg" ] || [ "$fg" = starship ]; } && [ "$i" -lt 15 ]; do
        sleep 0.2
        fg=$(_tuios_fg "$tty")
        i=$((i + 1))
      done
      case "$fg" in
        zsh | bash | sh) _tuios_cmd send-text -s "$s" -w "$wid" $'nvim\n' >/dev/null ;;
      esac
    done
}

# Session $1 for directory $2, the dev layout: workspace 1 holds nvim, aidev's Claude, Lumo and the builders. The pane
# `tuios new` opens becomes nvim; its command is typed into a shell, so quitting nvim leaves
# the pane at a prompt. A session that exists (still running, or restored by the daemon) keeps its layout and only
# gets nvim, Claude and Lumo back (_tuios_restore).
_tuios_devlayout() {
  local s="$1" dir="$2" first
  _tuios_daemon_up
  if _tuios_session_exists "$s"; then
    _tuios_restore "$s"
    return 0
  fi
  _tuios_cmd new "$s" -d --cwd "$dir" >/dev/null || return 1
  first=$(_tuios_cmd list-windows -s "$s" --json | jq -r '.windows[0].window_id')
  _tuios_cmd set-window -s "$s" -w "$first" --name nvim >/dev/null
  _tuios_cmd send-text -s "$s" -w nvim $'nvim\n' >/dev/null
  # No Claude or Lumo until you choose: the picker pane checks which models are usable and starts the one you pick.
  # A non-interactive zsh can start with a PATH lacking /opt/homebrew/bin, where python3 is Apple's 3.9.
  _tuios_cmd new-window pick -s "$s" --workspace 1 --cwd "$dir" --no-focus \
    --grants read,write,fan,files,respond,admin -- /bin/zsh -c \
    "export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:\$PATH; AIDEV_TUIOS_SESSION=$s python3 \$HOME/.config/aistack-tuios/aidev_pick.py" >/dev/null
  _tuios_cmd select-workspace 1 -s "$s" >/dev/null
  _tuios_cmd focus-window nvim -s "$s" >/dev/null
}

# A restored session's nvim, Claude and Lumo (tuios brings the windows back with fresh shells): nvim is typed in
# again, Claude and Lumo start again from their launchers with their conversations (aidev_tuios.py restore).
_tuios_restore() {
  _tuios_restore_nvim "$1"
  python3 "$HOME/.config/aistack-tuios/aidev_tuios.py" restore "$1"
}

# Reattaches to the sessions the daemon holds (each gets nvim, Claude and Lumo back), to nix-darwin's when there is
# one. With no session at all it creates the dev layout for ~/nix-darwin, ~/pscloudops/terraform-infrastructure and
# ~/home-infrastructure, each only where it is cloned, then attaches to nix-darwin's (else the first one).
dev() {
  _tuios_guard || return 1
  local s first="" spec detached=0
  [ "$1" = "--detached" ] && detached=1 && shift
  _tuios_daemon_up
  for s in $(_tuios_cmd ls --json 2>/dev/null | jq -r '.[]?.name'); do
    _tuios_restore "$s"
    [ -z "$first" ] && first="$s"
  done
  if [ -z "$first" ]; then
    for spec in nix-darwin:"$HOME/nix-darwin" terraform-infrastructure:"$HOME/pscloudops/terraform-infrastructure" \
      home-infrastructure:"$HOME/home-infrastructure"; do
      [ -d "${spec#*:}" ] || continue
      _tuios_devlayout "${spec%%:*}" "${spec#*:}" || continue
      [ -z "$first" ] && first="${spec%%:*}"
    done
  fi
  # Ensure nix-darwin and home-infrastructure sessions exist where directories are cloned
  for spec in nix-darwin:"$HOME/nix-darwin" home-infrastructure:"$HOME/home-infrastructure"; do
    [ -d "${spec#*:}" ] || continue
    _tuios_session_exists "${spec%%:*}" && continue
    _tuios_devlayout "${spec%%:*}" "${spec#*:}" || continue
  done
  # Call _tuios_dev_peer after local sessions exist, but before final attach
  if [ "$detached" -eq 0 ]; then
    _tuios_dev_peer
  fi
  if [ "$detached" -eq 0 ]; then
    if _tuios_session_exists nix-darwin; then
      _tuios_attach nix-darwin
    elif [ -n "$first" ]; then
      _tuios_attach "$first"
    fi
  fi
}

# Like devim: the current directory, named after it (or $1), always a new session (-2, -3... when the name is taken).
devim() {
  _tuios_guard || return 1
  local name="${1:-${PWD:t}}" s n=2
  s="$name"
  while _tuios_session_exists "$s"; do
    s="$name-$n"
    n=$((n + 1))
  done
  _tuios_devlayout "$s" "$PWD" && _tuios_attach "$s"
}

