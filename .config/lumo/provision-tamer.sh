#!/bin/zsh
# Idempotent: make $LUMO_TAMER_DIR a build of lumo-tamer pinned to $TAMER_REV. Run in the background
# from the nix-darwin activation (nix-modules/macos/lumo.nix); log: $LUMO_TAMER_DIR/provision.log.
# Needs git, node/npm (Homebrew) and Go (the `login` auth helper; the `browser` method does not).
# It never touches config.yaml, secrets/ or sessions/ (all git-ignored), so auth survives updates.
source "${0:A:h}/lumo-common.sh"

TAMER_REPO=${TAMER_REPO:-https://github.com/ZeroTricks/lumo-tamer.git}
TAMER_REV=${1:?usage: provision-tamer.sh <full commit sha>}
LOG=$LUMO_TAMER_DIR.provision.log
log() { print -r -- "$(date '+%Y-%m-%d %H:%M:%S') [lumo-tamer-provisioner] $*" | tee -a "$LOG"; }

for tool in git node npm; do
  command -v $tool >/dev/null || { log "ERROR: $tool not found, skipping"; exit 1; }
done

if [[ ! -d $LUMO_TAMER_DIR/.git ]]; then
  log "cloning $TAMER_REPO"
  git clone --quiet "$TAMER_REPO" "$LUMO_TAMER_DIR" >>"$LOG" 2>&1 || { log "ERROR: clone failed"; exit 1; }
fi
cd "$LUMO_TAMER_DIR" || exit 1

head=$(git rev-parse HEAD)
if [[ $head != $TAMER_REV ]]; then
  log "checking out pinned revision $TAMER_REV (was $head)"
  git fetch --quiet origin >>"$LOG" 2>&1
  git checkout --quiet --force "$TAMER_REV" >>"$LOG" 2>&1 || { log "ERROR: checkout failed"; exit 1; }
  rm -rf dist
fi

# Loopback-only hosts: lumo-tamer listens on every interface and has no setting for the address, so make the one
# listen() call read LUMO_TAMER_HOST (run-tamer.sh sets it to 127.0.0.1 and refuses to start an unpatched build).
# The LAN host is left exactly as upstream ships it.
SERVER_TS=src/api/server.ts
if [[ $LUMO_LAN != 1 ]] && ! grep -q LUMO_TAMER_HOST $SERVER_TS; then
  /usr/bin/perl -0pi -e 's/this\.expressApp\.listen\(this\.serverConfig\.port, \(\) => \{/this.expressApp.listen(this.serverConfig.port, process.env.LUMO_TAMER_HOST ?? "::", () => {/' $SERVER_TS
  if grep -q LUMO_TAMER_HOST $SERVER_TS; then
    log "patched $SERVER_TS to bind to LUMO_TAMER_HOST; rebuilding"
    rm -rf dist
  else
    log "ERROR: could not patch $SERVER_TS (listen call not found); tamer will not start on this host"
    exit 1
  fi
fi

if [[ ! -d dist || ! -d node_modules ]]; then
  log "building (npm ci && npm run build:all)"
  { npm ci --no-audit --no-fund && npm run build:all && npm link; } >>"$LOG" 2>&1 \
    || { log "ERROR: build failed, see $LOG"; exit 1; }
  log "build complete"
else
  log "already at $TAMER_REV and built"
fi
