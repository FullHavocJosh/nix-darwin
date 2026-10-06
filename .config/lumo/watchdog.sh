#!/bin/zsh
# lumo-tamer watchdog, run every 5 minutes by launchd (nix-modules/macos/lumo.nix).
#
# Checks (cheap first):
#   1. `tamer auth status` reports valid auth        -> reason "auth"
#   2. tamer's /v1/models answers with the API key   -> reason "server"
#   3. every 30 min, a real one-word Lumo request    -> reason "probe" (catches revoked tokens)
# On failure it alerts via ntfy (state change, then every 6 h while still failing) and, when
# enabled, tries `tamer auth browser` against a headless Chromium profile that is already
# signed in to Lumo. It also alerts on recovery.
#
# Optional Doppler secrets (FullHavocJosh/root_macmini):
#   LUMO_NTFY_URL    full topic URL, e.g. https://<ntfy host>/<topic>   (no alerts without it)
#   LUMO_NTFY_TOKEN  ntfy access token (Bearer)
# Auto re-auth is on only when the file ~/.lumo-watchdog/auto-reauth exists AND the profile dir
# ~/.lumo-chromium exists (sign in to https://lumo.proton.me once with that --user-data-dir).
# LUMO_WATCHDOG_DRYRUN=1 prints alerts instead of sending them.
source "${0:A:h}/lumo-common.sh"

STATE_DIR=${LUMO_WATCHDOG_DIR:-$HOME/.lumo-watchdog}
PROFILE=${LUMO_CHROMIUM_PROFILE:-$HOME/.lumo-chromium}
CHROMIUM=${LUMO_CHROMIUM:-/Applications/Chromium.app/Contents/MacOS/Chromium}
CDP_PORT=${LUMO_CDP_PORT:-9222}
PROBE_EVERY=1800 ALERT_EVERY=21600 REAUTH_EVERY=3600
mkdir -p "$STATE_DIR"; chmod 700 "$STATE_DIR"
now=$(date +%s)

# launchd appends to these forever; truncate in place (safe with the daemons running) past 5 MB
for f in $HOME/Library/Logs/lumo-*.log(N); do
  (( $(stat -f%z "$f") > 5242880 )) && : > "$f"
done

state_get() { cat "$STATE_DIR/$1" 2>/dev/null || echo "${2:-}"; }
state_set() { print -r -- "$2" > "$STATE_DIR/$1"; }
log() { print -r -- "$(date '+%Y-%m-%d %H:%M:%S') $*"; }

notify() { # title, body, priority
  if [[ -n ${LUMO_WATCHDOG_DRYRUN:-} ]]; then log "DRYRUN ntfy: [$1] $2"; return; fi
  local url=${NTFY_URL:-$(lumo_secret LUMO_NTFY_URL)} token=${NTFY_TOKEN:-$(lumo_secret LUMO_NTFY_TOKEN)}
  [[ -z $url ]] && { log "no LUMO_NTFY_URL: not sending [$1]"; return; }
  local auth=(); [[ -n $token ]] && auth=(-H "Authorization: Bearer $token")
  curl -s -m 15 -o /dev/null "${auth[@]}" -H "Title: $1" -H "Priority: ${3:-default}" -H "Tags: lock" \
    -d "$2" "$url" || log "ntfy post failed"
}

api_key=$(lumo_secret LUMO_TAMER_API_KEY); [[ -z $api_key ]] && api_key=$(lumo_tamer_key)
base=${LUMO_TAMER_URL:-http://127.0.0.1:$LUMO_TAMER_PORT/v1}

check() { # echoes "ok" or a failure reason
  local out
  out=$(cd "$LUMO_TAMER_DIR" && tamer auth status 2>&1)
  [[ $out == *"Authentication is configured and valid"* ]] || { echo auth; return; }
  curl -s -m 10 -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $api_key" "$base/models" \
    | grep -q '^200$' || { echo server; return; }
  if (( now - $(state_get last_probe 0) >= PROBE_EVERY )); then
    local reply
    reply=$(curl -s -m 60 -H "Authorization: Bearer $api_key" -H 'Content-Type: application/json' \
      -d '{"model":"lumo-lite","messages":[{"role":"user","content":"Reply with the single word: ok"}]}' \
      "$base/chat/completions")
    [[ $reply == *'"content"'* ]] || { echo probe; return; }
    state_set last_probe $now
  fi
  echo ok
}

reauth() { # returns 0 when auth was refreshed
  [[ -f $STATE_DIR/auto-reauth && -d $PROFILE && -x $CHROMIUM ]] || return 1
  (( now - $(state_get last_reauth 0) >= REAUTH_EVERY )) || return 1
  state_set last_reauth $now
  log "auto re-auth: starting headless Chromium on profile $PROFILE"
  "$CHROMIUM" --headless=new --remote-debugging-address=127.0.0.1 --remote-debugging-port=$CDP_PORT \
    --user-data-dir="$PROFILE" https://lumo.proton.me >/dev/null 2>&1 &
  local pid=$! i
  for i in {1..30}; do curl -s -m 2 "http://127.0.0.1:$CDP_PORT/json/version" >/dev/null && break; sleep 1; done
  # tamer prompts for the CDP endpoint; an empty line accepts the configured default. Cap the run.
  (cd "$LUMO_TAMER_DIR" && print '' | /usr/bin/perl -e 'alarm shift; exec @ARGV' 180 tamer auth browser) >/dev/null 2>&1
  kill $pid 2>/dev/null; sleep 2; kill -9 $pid 2>/dev/null
  # the daemon's KeepAlive restarts tamer with the new vault
  pkill -f "tamer server" 2>/dev/null; sleep 12
  [[ $(check) == ok ]]
}

result=$(check)
prev=$(state_get status ok)
if [[ $result == ok ]]; then
  [[ $prev != ok ]] && notify "Lumo tamer recovered" "Auth and server are healthy again on $(hostname -s)." default
  state_set status ok; exit 0
fi

log "check failed: $result"
if [[ $result == auth || $result == probe ]] && reauth; then
  log "auto re-auth succeeded"
  notify "Lumo tamer re-authenticated" "Failed with '$result'; refreshed automatically from the headless Chromium profile." default
  state_set status ok; exit 0
fi

if [[ $prev == ok || $now -ge $(( $(state_get last_alert 0) + ALERT_EVERY )) ]]; then
  case $result in
    auth|probe) hint="Lumo sign-in expired or was revoked. On your MacBook run: lumoreauth (opens Chromium, you sign in once, it hands the session to this Mini and restarts tamer). Interactive because of Proton CAPTCHA/2FA." ;;
    server)     hint="tamer server is not answering on $base. Check ~/Library/Logs/lumo-tamer.log and 'launchctl print system/org.nixos.lumo-tamer'." ;;
  esac
  notify "Lumo tamer: $result failing" "$hint" high
  state_set last_alert $now
fi
state_set status "$result"
exit 1
