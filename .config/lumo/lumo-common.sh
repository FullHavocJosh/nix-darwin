# Shared by the lumo-* scripts (sourced, not executed). zsh.
# Secrets come from Doppler (FullHavocJosh/root_macmini); every value is optional so a
# daemon still starts from the local files when Doppler is unreachable.
export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
export HOME=${HOME:-/Users/havoc}

LUMO_TAMER_DIR=${LUMO_TAMER_DIR:-$HOME/lumo-tamer}
LUMO_TAMER_PORT=${LUMO_TAMER_PORT:-3003}
LUMO_PLANNER_PORT=${LUMO_PLANNER_PORT:-8765}
# LUMO_LAN=1 (the desktop, set by nix-modules/macos/lumo.nix): tamer and the planner serve the whole network.
# Anything else (the laptop): both listen on 127.0.0.1 only, with the host's own Proton sign-in.
# Every device has its OWN planner key, LUMO_PLANNER_API_KEY in that device's Doppler config (root_macmini for the
# desktop, root_macbook for the laptop). reauth.sh replaces it each time the device is signed in again.
# The laptop's tamer and vault keys stay on the laptop and are never read from Doppler.
LUMO_LAN=${LUMO_LAN:-0}
LUMO_DOPPLER_PROJECT=${LUMO_DOPPLER_PROJECT:-FullHavocJosh}
if [[ $LUMO_LAN == 1 ]]; then
  LUMO_DOPPLER_CONFIG=${LUMO_DOPPLER_CONFIG:-root_macmini}
else
  LUMO_DOPPLER_CONFIG=${LUMO_DOPPLER_CONFIG:-root_macbook}
fi
# Last planner key this device read from Doppler (mode 600). The laptop starts from it when Doppler cannot be
# reached (off the network), and the local clients (aistack, aidev) read it to talk to the local planner.
LUMO_PLANNER_KEY_FILE=${LUMO_PLANNER_KEY_FILE:-$HOME/.lumo-planner-key}

# lumo_secret NAME -> value on stdout, empty when unset or Doppler is unreachable
lumo_secret() {
  doppler secrets get "$1" --project "$LUMO_DOPPLER_PROJECT" --config "$LUMO_DOPPLER_CONFIG" \
    --plain 2>/dev/null
}

# lumo_key_secret NAME -> like lumo_secret, but only on the LAN host. A loopback-only host must not pick up the
# desktop's server, planner or vault keys, so there it always prints nothing and the local files are used.
lumo_key_secret() {
  [[ $LUMO_LAN == 1 ]] && lumo_secret "$1"
}

# lumo_planner_key -> this device's planner key: from Doppler (and remembered in the key file), else the key file
lumo_planner_key() {
  local k
  k=$(lumo_secret LUMO_PLANNER_API_KEY)
  if [[ -n $k ]]; then
    (umask 077; print -r -- "$k" > "$LUMO_PLANNER_KEY_FILE")
  else
    k=$(cat "$LUMO_PLANNER_KEY_FILE" 2>/dev/null)
  fi
  print -r -- "$k"
}

# lumo_tamer_key -> the apiKey tamer's config.yaml serves with
lumo_tamer_key() {
  sed -n 's/^ *apiKey: *"\(.*\)" *$/\1/p' "$LUMO_TAMER_DIR/config.yaml" 2>/dev/null | head -1
}
