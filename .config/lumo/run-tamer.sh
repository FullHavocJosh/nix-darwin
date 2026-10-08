#!/bin/zsh
# lumo-tamer server, run by launchd (nix-modules/macos/lumo.nix). Never prints secrets.
#
# Vault key: the encrypted token vault (sessions/vault.enc) can only be opened with the key in
# secrets/lumo-vault-key. An existing key file is NEVER overwritten (a different key would make
# the vault unreadable); Doppler LUMO_VAULT_KEY only restores a missing file, e.g. a fresh machine.
# Server key: Doppler LUMO_TAMER_API_KEY wins; otherwise config.yaml keeps its current key, and a
# first run generates one.
# Doppler is only consulted on the LAN host (LUMO_LAN=1). A loopback-only host generates and keeps its own keys.
# Bind address: lumo-tamer has no setting for it, so provision-tamer.sh patches the build to read LUMO_TAMER_HOST.
# A loopback-only host refuses to start a build without that patch rather than listen on every interface.
source "${0:A:h}/lumo-common.sh"
cd "$LUMO_TAMER_DIR" || { echo "lumo-tamer not provisioned at $LUMO_TAMER_DIR" >&2; exit 1; }
umask 077

mkdir -p secrets
if [[ ! -s secrets/lumo-vault-key ]]; then
  vault_key=$(lumo_key_secret LUMO_VAULT_KEY)
  if [[ -n $vault_key ]]; then
    print -r -- "$vault_key" > secrets/lumo-vault-key
  else
    echo "no vault key file and none in Doppler: creating a new one (tokens must be re-authenticated)" >&2
    openssl rand -base64 32 > secrets/lumo-vault-key
  fi
fi

api_key=$(lumo_key_secret LUMO_TAMER_API_KEY)
[[ -z $api_key ]] && api_key=$(lumo_tamer_key)
[[ -z $api_key ]] && api_key=$(openssl rand -hex 24)
cat > config.yaml <<EOF
auth:
  vault:
    keyFilePath: "$LUMO_TAMER_DIR/secrets/lumo-vault-key"
server:
  port: $LUMO_TAMER_PORT
  apiKey: "$api_key"
  enableWebSearch: true
EOF

if [[ $LUMO_LAN != 1 ]]; then
  if ! grep -q LUMO_TAMER_HOST dist/src/api/server.js 2>/dev/null; then
    echo "this lumo-tamer build cannot bind to loopback only (provision-tamer.sh has not patched it yet): not starting" >&2
    sleep 30   # launchd restarts this job; the provisioner may still be building
    exit 1
  fi
  export LUMO_TAMER_HOST=127.0.0.1
fi

exec tamer server
