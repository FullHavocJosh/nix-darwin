# Shared by the lumo-* scripts (sourced, not executed). zsh.
# Secrets come from Doppler (FullHavocJosh/root_macmini); every value is optional so a
# daemon still starts from the local files when Doppler is unreachable.
export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
export HOME=${HOME:-/Users/havoc}

LUMO_TAMER_DIR=${LUMO_TAMER_DIR:-$HOME/lumo-tamer}
LUMO_TAMER_PORT=${LUMO_TAMER_PORT:-3003}
LUMO_PLANNER_PORT=${LUMO_PLANNER_PORT:-8765}
# LUMO_LAN=1 (the desktop, set by nix-modules/macos/lumo.nix): tamer and the planner serve the whole network, on
# purpose (other machines and services use the Mini's Lumo), behind the keys in Doppler FullHavocJosh/root_macmini.
# Those keys are static: other services are configured with them, so nothing here ever replaces them.
# Anything else (the laptop): both listen on 127.0.0.1 only, with the host's own Proton sign-in and its own locally
# generated tamer and vault keys. The laptop's planner has no key: only this machine can reach it.
LUMO_LAN=${LUMO_LAN:-0}
LUMO_DOPPLER_PROJECT=${LUMO_DOPPLER_PROJECT:-FullHavocJosh}
LUMO_DOPPLER_CONFIG=${LUMO_DOPPLER_CONFIG:-root_macmini}

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

# lumo_tamer_key -> the apiKey tamer's config.yaml serves with
lumo_tamer_key() {
  sed -n 's/^ *apiKey: *"\(.*\)" *$/\1/p' "$LUMO_TAMER_DIR/config.yaml" 2>/dev/null | head -1
}
