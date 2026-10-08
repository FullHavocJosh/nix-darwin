#!/bin/zsh
# lumoreauth: sign in to Lumo on THIS machine and hand the session to the Mac Mini's tamer.
# The Mini is headless, so the browser runs here and `tamer auth browser` on the Mini reads it through an
# SSH reverse tunnel to this browser's debug port. Needs Proton's CAPTCHA/2FA, so it is interactive.
#
#   lumoreauth           sign in, hand over, restart tamer, verify
#   lumoreauth --check   everything except the handover: Chromium starts, the tunnel carries its debug port
#                        to the Mini. Changes nothing on the Mini.
#   lumoauth             (this script with --local) sign in and give the session to THIS machine's own tamer, the
#                        loopback-only one a laptop runs. No ssh, nothing on the Mini changes. Each machine gets its
#                        own sign-in this way: sign in again for the Mini with lumoreauth, never share one session.
# This script only handles the Proton sign-in. It never reads or changes an API key: the Mini's keys are static
# (other services use them) and the laptop's planner has none.
#
# Why a throwaway profile: lumo-tamer's docs say not to reuse the same tokens on two machines. The session
# handed to the Mini must not stay in a browser that could refresh it, so the profile is deleted on exit.
MINI=${LUMO_MINI_HOST:-macminim1.rollet.family}
MINI_USER=${LUMO_MINI_USER:-havoc}
SSH_KEY=${LUMO_SSH_KEY:-$HOME/.ssh/id_ed25519}
CHROMIUM=${LUMO_CHROMIUM:-/Applications/Chromium.app/Contents/MacOS/Chromium}
LOCAL_PORT=${LUMO_CDP_PORT:-9222}
REMOTE_PORT=${LUMO_CDP_REMOTE_PORT:-19222}
CHECK=0 LOCAL=0
for arg in "$@"; do
  case $arg in
    --check) CHECK=1 ;;
    --local) LOCAL=1 ;;
    *) print -u2 -r -- "lumoreauth: unknown option $arg"; exit 2 ;;
  esac
done

SSH=(ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=8 "$MINI_USER@$MINI")
PROFILE=$(mktemp -d "${TMPDIR:-/tmp}/lumo-reauth.XXXXXX") || exit 1
CHROMIUM_PID=""
cleanup() {
  [[ -n $CHROMIUM_PID ]] && kill $CHROMIUM_PID 2>/dev/null && sleep 1 && kill -9 $CHROMIUM_PID 2>/dev/null
  rm -rf "$PROFILE"
}
trap cleanup EXIT INT TERM
die() { print -u2 -r -- "lumoreauth: $*"; exit 1; }

[[ -x $CHROMIUM ]] || die "Chromium not found at $CHROMIUM (set LUMO_CHROMIUM)"
lsof -nP -iTCP:$LOCAL_PORT -sTCP:LISTEN >/dev/null 2>&1 && die "port $LOCAL_PORT is already in use; quit any Chromium started with --remote-debugging-port"
(( LOCAL )) || "${SSH[@]}" true 2>/dev/null || die "cannot ssh to $MINI_USER@$MINI with $SSH_KEY"

print "Starting Chromium with a temporary profile..."
"$CHROMIUM" --remote-debugging-port=$LOCAL_PORT --remote-debugging-address=127.0.0.1 --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check https://lumo.proton.me >/dev/null 2>&1 &
CHROMIUM_PID=$!
for i in {1..30}; do curl -s -m 2 "http://127.0.0.1:$LOCAL_PORT/json/version" >/dev/null && break; sleep 1; done
curl -s -m 2 "http://127.0.0.1:$LOCAL_PORT/json/version" >/dev/null || die "Chromium's debug port did not come up"

TUNNEL=(-o ExitOnForwardFailure=yes -R 127.0.0.1:$REMOTE_PORT:127.0.0.1:$LOCAL_PORT)
if (( CHECK )); then
  out=$("${SSH[@]}" "${TUNNEL[@]}" "curl -s -m 5 http://127.0.0.1:$REMOTE_PORT/json/version | head -c 120" 2>&1)
  [[ $out == *Browser* ]] || die "tunnel check failed: $out"
  print "check ok: Chromium's debug port is reachable from the Mini through the tunnel. Nothing was changed."
  exit 0
fi

print "In the Chromium window, sign in to Lumo (password, 2FA, CAPTCHA) until you see your Lumo chat."
read -r "?Press Enter when Lumo shows the chat signed in (Ctrl-C to abort): "

if (( LOCAL )); then
  print "Handing the session to this machine's tamer..."
  (export PATH=/opt/homebrew/bin:$PATH; cd ~/lumo-tamer && echo http://127.0.0.1:$LOCAL_PORT | tamer auth browser) \
    || die "tamer auth browser failed; the old session was left as it was"
  print "Restarting tamer so it loads the new session (launchd starts it again)..."
  pkill -f "tamer server"; sleep 15
  (export PATH=/opt/homebrew/bin:$PATH; cd ~/lumo-tamer && tamer auth status 2>&1 | grep -E "Summary|valid|attention|expiresIn")
  print "Done. This browser profile is deleted on exit; do not sign in to Lumo in it again."
  exit 0
fi

print "Handing the session to tamer on $MINI..."
"${SSH[@]}" "${TUNNEL[@]}" "export PATH=/opt/homebrew/bin:\$PATH; cd ~/lumo-tamer && echo http://127.0.0.1:$REMOTE_PORT | tamer auth browser" \
  || die "tamer auth browser failed on the Mini; the old session was left as it was"

print "Restarting tamer so it loads the new session..."
"${SSH[@]}" 'pkill -f "tamer server"; sleep 15; export PATH=/opt/homebrew/bin:$PATH; cd ~/lumo-tamer && tamer auth status 2>&1 | grep -E "Summary|valid|attention|expiresIn"'
print "Done. This browser profile is deleted on exit; do not sign in to Lumo in it again."
