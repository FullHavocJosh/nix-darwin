#!/bin/zsh
# lumo-planner proxy (OpenAI-compatible, tool-less), run by launchd (nix-modules/macos/lumo.nix).
# Lumo talks to the local tamer server; repo files are served from $LUMO_PLANNER_ROOT.
# LAN host (LUMO_LAN=1): serves every device and needs LUMO_PLANNER_API_KEY from Doppler (lumo_planner.py refuses
# a non-loopback bind without a key). If Doppler does not answer, this exits and launchd tries again; it used to fall
# back to loopback for good, which left the other devices without Lumo until someone restarted it by hand.
# Any other host: loopback only, with this device's own key (Doppler root_macbook, or the copy in the key file when
# Doppler cannot be reached). Before the first `lumoauth` there is no key yet and loopback is served without one.
source "${0:A:h}/lumo-common.sh"

export LUMO_BASE_URL="http://127.0.0.1:$LUMO_TAMER_PORT/v1"
export LUMO_MODEL=${LUMO_MODEL:-lumo}
export LUMO_API_KEY=$(lumo_key_secret LUMO_TAMER_API_KEY)
[[ -z $LUMO_API_KEY ]] && export LUMO_API_KEY=$(lumo_tamer_key)

if [[ $LUMO_LAN == 1 ]]; then
  planner_key=""
  for attempt in {1..6}; do
    planner_key=$(lumo_secret LUMO_PLANNER_API_KEY)
    [[ -n $planner_key ]] && break
    echo "LUMO_PLANNER_API_KEY not readable from Doppler (attempt $attempt of 6)" >&2
    sleep 10
  done
  if [[ -z $planner_key ]]; then
    echo "no LUMO_PLANNER_API_KEY: not starting, launchd will retry" >&2
    exit 1
  fi
  (umask 077; print -r -- "$planner_key" > "$LUMO_PLANNER_KEY_FILE")
  export PLANNER_API_KEY=$planner_key LUMO_PLANNER_HOST=${LUMO_PLANNER_HOST:-0.0.0.0}
else
  planner_key=$(lumo_planner_key)
  if [[ -n $planner_key ]]; then
    export PLANNER_API_KEY=$planner_key
  else
    echo "no planner key for this device yet (run lumoauth): serving loopback without one" >&2
  fi
  export LUMO_PLANNER_HOST=127.0.0.1
fi
export LUMO_PLANNER_PORT

exec python3 "${0:A:h}/lumo_planner.py" serve -r "${LUMO_PLANNER_ROOT:-$HOME/home-infrastructure}"
