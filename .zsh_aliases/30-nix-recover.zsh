# nix-recover -- load the nix launchd daemons by hand when macOS did not start them at boot.
#
# Background Task Management (sfltool dumpbtm) can mark the nix daemons "disallowed"; System Settings lists them as
# "sh" from an unknown developer, and macOS updates reset them. launchd then skips them at boot: /nix stays locked,
# activate-system never recreates /run/current-system, and `sudo darwin-rebuild` fails with "command not found".
# A manual launchctl bootstrap is not gated by BTM, so this loads them until the next reboot. The lasting fix is an
# MDM com.apple.servicemanagement LabelPrefix rule for org.nixos. and family.rollet. (it cannot be installed locally).
# Runs before any command line containing darwin-rebuild (preexec hook below) and before darwin-reload.
function nix-recover() {
  [[ "$OSTYPE" == darwin* ]] || return 0
  [[ -d /nix/store && -e /run/current-system ]] && return 0
  echo "nix-recover: the nix launchd daemons did not start at boot (Background Task Management). Loading them..." >&2
  local label plist i
  # keepalive unlocks the /nix volume; activate-system waits for /nix/store, then recreates /run/current-system
  for label in family.rollet.nix-store-keepalive org.nixos.activate-system org.nixos.nix-daemon; do
    plist="/Library/LaunchDaemons/$label.plist"
    [[ -f "$plist" ]] || continue
    launchctl print "system/$label" >/dev/null 2>&1 || sudo launchctl bootstrap system "$plist"
  done
  for i in {1..60}; do
    [[ -e /run/current-system ]] && { echo "nix-recover: /run/current-system is back." >&2; return 0; }
    sleep 1
  done
  echo "nix-recover: /run/current-system is still missing after 60s. Check: ls /nix/store; sudo launchctl print system/org.nixos.activate-system" >&2
  return 1
}
function _nix_recover_preexec() {
  # not `[[ ]] && ...`: a non-matching line must return 0, or a `source ~/.zshrc* && ...` chain stops here
  [[ "$1" == *darwin-rebuild* ]] || return 0
  nix-recover
}

