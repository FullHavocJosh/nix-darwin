
alias lumoreauth='zsh ~/.config/lumo/reauth.sh'
alias lumoauth='zsh ~/.config/lumo/reauth.sh --local'

# Lumo sign-in state of this machine ($1 empty) or of the ssh target in $1: prints valid, invalid, building
# (provision-tamer.sh is running, or tamer is built and its daemon has not written config.yaml yet, which is the case
# right after a first switch), missing (not built and no provisioner running: that host has not been switched since
# the tamer directory changed, or its provisioning failed), or unreachable (the ssh connection itself failed, which
# says nothing about the sign-in).
function _lumo_signin_state() {
  local check='export PATH=/opt/homebrew/bin:$PATH; d=$HOME/lumo-tamer-fullhavoc
if [ ! -d "$d/dist" ] || [ ! -f "$d/config.yaml" ]; then
  if pgrep -qf provision-tamer.sh || [ -d "$d/dist" ]; then echo building; else echo missing; fi
  exit 0
fi
cd "$d" && tamer auth status 2>&1'
  local out
  if [[ -n "$1" ]]; then
    # -n: this runs from a prompt hook, so ssh must not read (and swallow) what is typed ahead at the terminal
    out=$(ssh -n -o BatchMode=yes -o ConnectTimeout=8 "$1" "$check" 2>&1)
    [[ $? -eq 255 ]] && { echo unreachable; return 0; }
  else
    out=$(/bin/sh -c "$check" 2>&1)
  fi
  case "$out" in
    building|missing) echo "$out" ;;
    *"Authentication is configured and valid"*) echo valid ;;
    *) echo invalid ;;
  esac
}

# After a switch: start the browser sign-in for $1 (laptop|desktop) when its session is not valid. $2 = ssh target
# when the desktop was switched from another Mac. $3 = nowait: check once, do not wait for a provisioner (for a host
# this switch did not touch).
function _lumo_signin_if_invalid() {
  local host="$1" remote="$2" nowait="$3" state i
  # a first switch builds lumo-tamer in the background and its daemon then writes config.yaml: give it 2 minutes
  for i in {1..12}; do
    state=$(_lumo_signin_state "$remote")
    [[ "$state" == building && "$nowait" != nowait ]] || break
    (( i == 1 )) && echo "Lumo: lumo-tamer${remote:+ on MacMiniM1} is still being set up, waiting up to 2 minutes..."
    sleep 10
  done
  case "$state" in
    valid) echo "Lumo: Proton sign-in${remote:+ on MacMiniM1} is valid, nothing to do."; return 0 ;;
    unreachable) echo "Lumo: could not reach $remote over ssh, so its sign-in was not checked."; return 0 ;;
    building)
      echo "Lumo: lumo-tamer${remote:+ on MacMiniM1} is not ready yet (tail ~/lumo-tamer-fullhavoc.provision.log). Sign in afterwards with: ${${host:#desktop}:+lumoauth}${${host:#laptop}:+lumoreauth}"
      return 0 ;;
    missing)
      echo "Lumo: lumo-tamer${remote:+ on MacMiniM1} is not set up in ~/lumo-tamer-fullhavoc and no provisioner is running. Run: darwin-reload switch $host (if that does not fix it: tail ~/lumo-tamer-fullhavoc.provision.log)"
      return 0 ;;
  esac
  if [[ "$host" == laptop ]]; then
    echo "Lumo: the Proton sign-in on this machine is not valid. Starting the browser sign-in (lumoauth)..."
    zsh ~/.config/lumo/reauth.sh --local
  elif [[ -n "$remote" ]]; then
    echo "Lumo: the Proton sign-in on MacMiniM1 is not valid. Starting the browser sign-in here (lumoreauth)..."
    zsh ~/.config/lumo/reauth.sh
  else
    echo "Lumo: the Proton sign-in on this machine is not valid, and it has no screen. Run lumoauth here (Helium opens on the MacBook) or lumoreauth on the MacBook"
  fi
}

