#!/bin/zsh
# lumo-tamer server, run by launchd (nix-modules/macos/lumo.nix). Never prints secrets.
#
# Vault key: the encrypted token vault (sessions/vault.enc) can only be opened with the key in
# secrets/lumo-vault-key. An existing key file is NEVER overwritten (a different key would make
# the vault unreadable); Doppler LUMO_VAULT_KEY only restores a missing file, e.g. a fresh machine.
# Server key: Doppler LUMO_TAMER_API_KEY wins; otherwise config.yaml keeps its current key, and a
# first run generates one.
source "${0:A:h}/lumo-common.sh"
cd "$LUMO_TAMER_DIR" || { echo "lumo-tamer not provisioned at $LUMO_TAMER_DIR" >&2; exit 1; }
umask 077

mkdir -p secrets
if [[ ! -s secrets/lumo-vault-key ]]; then
  vault_key=$(lumo_secret LUMO_VAULT_KEY)
  if [[ -n $vault_key ]]; then
    print -r -- "$vault_key" > secrets/lumo-vault-key
  else
    echo "no vault key file and none in Doppler: creating a new one (tokens must be re-authenticated)" >&2
    openssl rand -base64 32 > secrets/lumo-vault-key
  fi
fi

api_key=$(lumo_secret LUMO_TAMER_API_KEY)
[[ -z $api_key ]] && api_key=$(lumo_tamer_key)
[[ -z $api_key ]] && api_key=$(openssl rand -hex 24)
cat > config.yaml <<EOF
auth:
  vault:
    keyFilePath: "$LUMO_TAMER_DIR/secrets/lumo-vault-key"
server:
  port: $LUMO_TAMER_PORT
  apiKey: "$api_key"
EOF

exec tamer server
