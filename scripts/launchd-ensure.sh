#!/usr/bin/env bash
set -uo pipefail

# nix-darwin only reloads a service whose plist changed, so a service that dropped out of launchd stays down across
# darwin-rebuild switch. This script lints each managed plist and bootstraps every service launchd has not loaded.

usage() {
  echo "Usage: $0 [--check] [--user NAME] DOMAIN LABEL PLIST [DOMAIN LABEL PLIST ...]" >&2
  exit 2
}

check=false
user=
while [[ $# -gt 0 ]]; do
  case $1 in
    --check)
      check=true
      shift
      ;;
    --user)
      [[ $# -lt 2 ]] && usage
      user="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -eq 0 ]] || [[ $(( $# % 3 )) -ne 0 ]]; then
  usage
fi

# Validate every triple before touching any service
triples=()
while [[ $# -gt 0 ]]; do
  [[ "$1" == "system" || "$1" == "gui" ]] || usage
  [[ "$1" == "gui" && -z "$user" ]] && usage
  triples+=("$1" "$2" "$3")
  shift 3
done

failed=false

for (( i=0; i<${#triples[@]}; i+=3 )); do
  domain="${triples[i]}"
  label="${triples[i+1]}"
  plist="${triples[i+2]}"

  if [[ ! -f "$plist" ]]; then
    echo "[launchd-ensure] warning: plist not found: $plist" >&2
    failed=true
    continue
  fi

  if ! /usr/bin/plutil -lint -s "$plist" >/dev/null 2>&1; then
    echo "[launchd-ensure] warning: invalid plist: $plist" >&2
    failed=true
    continue
  fi

  if [[ "$domain" == "gui" ]]; then
    if ! uid=$(id -u "$user" 2>/dev/null); then
      echo "[launchd-ensure] warning: no such user: $user" >&2
      failed=true
      continue
    fi
    resolved_domain="gui/$uid"
    if ! /bin/launchctl print "$resolved_domain" >/dev/null 2>&1; then
      echo "[launchd-ensure] skipped $label: no GUI session for $user"
      continue
    fi
  else
    resolved_domain="system"
  fi

  target="$resolved_domain/$label"

  if /bin/launchctl print "$target" >/dev/null 2>&1; then
    continue
  fi

  if [[ "$check" == true ]]; then
    echo "[launchd-ensure] warning: not loaded: $label" >&2
    failed=true
    continue
  fi

  /bin/launchctl enable "$target" >/dev/null 2>&1 || true
  /bin/launchctl bootstrap "$resolved_domain" "$plist" >/dev/null 2>&1 || true

  if /bin/launchctl print "$target" >/dev/null 2>&1; then
    echo "[launchd-ensure] loaded $label"
  else
    echo "[launchd-ensure] warning: failed to load $label" >&2
    failed=true
  fi
done

[[ "$failed" == true ]] && exit 1
exit 0
