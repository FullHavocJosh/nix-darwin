# _tuios_peer: prints two words <hostname> <user@address> for the other Mac, chosen by hostname -s
#   MacBookM2Pro prints macmini havoc@macminim1.rollet.family
#   MacMiniM1 prints macbookpro havoc@macbookm2pro.rollet.family
#   any other host prints nothing and returns 1
_tuios_peer() {
  case "$(hostname -s)" in
    MacBookM2Pro) echo "macmini havoc@macminim1.rollet.family" ;;
    MacMiniM1) echo "macbookpro havoc@macbookm2pro.rollet.family" ;;
    *) return 1 ;;
  esac
}

# _tuios_peer_up <user@address>: returns 0 only when ssh succeeds with BatchMode=yes and ConnectTimeout=3
_tuios_peer_up() {
  ssh -o BatchMode=yes -o ConnectTimeout=3 -i ~/.ssh/id_ed25519 "$1" true >/dev/null 2>&1
}

# _tuios_peer_link <name> <user@address>: the host links live in .config/tuios/config.toml, never added from here.
# If _tuios_cmd hosts output does not contain the name as a word, echo one line to stderr about 'tuios config apply'
_tuios_peer_link() {
  local name="$1" address="$2"
  if ! _tuios_cmd hosts 2>/dev/null | grep -qw "$name"; then
    echo "tuios: host $name is not linked yet; run 'tuios config apply' in a terminal outside tuios" >&2
  fi
}

# peerdev <session>: opens a session on the peer Mac through tuios host link
#   with no argument prints usage and returns 1
#   with unknown host returns 1 without calling tuios
#   with reachable host, calls _tuios_cmd switch-session <name>:<session> when $TUIOS_ENV is set
#   else calls _tuios_cmd attach --host <name> <session>
peerdev() {
  _tuios_guard || return 1
  [ -n "$1" ] || { echo "usage: peerdev <session>" >&2; return 1; }
  local peer name address
  peer=$(_tuios_peer) || { echo "tuios: no peer Mac known for this host" >&2; return 1; }
  name=${peer%% *}; address=${peer#* }; _tuios_peer_up "$address" || { echo "tuios: $name not reachable" >&2; return 1; }
  if [ -n "$TUIOS_ENV" ]; then
    _tuios_cmd switch-session "$name:$1";
  else
    _tuios_cmd attach --host "$name" "$1";
  fi
}

# mmdev opens a new session on the peer Mac
mmdev() {
  _tuios_guard || return 1
  local peer name address
  peer=$(_tuios_peer) || { echo "tuios: no peer Mac known for this host" >&2; return 1; }
  name=${peer%% *}; address=${peer#* }; _tuios_peer_up "$address" || { echo "tuios: $name not reachable" >&2; return 1; }
  _tuios_cmd new --host "$name" ${1:+"$1"};
}

alias nxpeer='peerdev nix-darwin'
alias hipeer='peerdev home-infrastructure'
alias nxmmdev=nxpeer
alias himmdev=hipeer

# _tuios_dev_peer: opens the other Mac sessions only when ssh answers, never fails dev;
# TUIOS_DEV_NO_PEER stops the remote dev from ssh-ing back
_tuios_dev_peer() {
  if [ -n "$TUIOS_DEV_NO_PEER" ]; then
    return 0
  fi
  local peer=$(_tuios_peer)
  if [ -z "$peer" ]; then
    return 0
  fi
  local name address
  name=${peer%% *}
  address=${peer#* }
  if ! _tuios_peer_up "$address"; then
    echo "tuios: $name not reachable, skipping" >&2
    return 0
  fi
  ssh -o BatchMode=yes -o ConnectTimeout=5 -i ~/.ssh/id_ed25519 "$address" "TUIOS_DEV_NO_PEER=1 zsh -ic 'dev --detached'" >/dev/null 2>&1 || {
    echo "tuios: $name: dev --detached failed" >&2
  }
  _tuios_peer_link "$name" "$address"
}
