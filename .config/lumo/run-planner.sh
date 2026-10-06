#!/bin/zsh
# lumo-planner proxy (OpenAI-compatible, tool-less), run by launchd (nix-modules/macos/lumo.nix).
# Lumo talks to the local tamer server; repo files are served from $LUMO_PLANNER_ROOT.
# Other devices may connect only when Doppler holds LUMO_PLANNER_API_KEY: without it the proxy
# stays on loopback (lumo_planner.py refuses a non-loopback bind without a key).
source "${0:A:h}/lumo-common.sh"

export LUMO_BASE_URL="http://127.0.0.1:$LUMO_TAMER_PORT/v1"
export LUMO_MODEL=${LUMO_MODEL:-lumo}
export LUMO_API_KEY=$(lumo_secret LUMO_TAMER_API_KEY)
[[ -z $LUMO_API_KEY ]] && export LUMO_API_KEY=$(lumo_tamer_key)

planner_key=$(lumo_secret LUMO_PLANNER_API_KEY)
if [[ -n $planner_key ]]; then
  export PLANNER_API_KEY=$planner_key LUMO_PLANNER_HOST=${LUMO_PLANNER_HOST:-0.0.0.0}
else
  echo "LUMO_PLANNER_API_KEY not in Doppler: serving on loopback only" >&2
fi
export LUMO_PLANNER_PORT

exec python3 "${0:A:h}/lumo_planner.py" serve -r "${LUMO_PLANNER_ROOT:-$HOME/home-infrastructure}"
