# darwin-reload -- darwin-rebuild for one of this repo's hosts, followed by the Lumo sign-in when it has expired.
#
#   darwin-reload switch laptop            this MacBook
#   darwin-reload switch desktop           MacMiniM1; from the MacBook it runs there over ssh
#   darwin-reload switch work
#   darwin-reload build laptop --show-trace   (build and check also work; extra arguments go to darwin-rebuild)
#
# After a successful switch of laptop or desktop it asks that machine's tamer whether the Proton sign-in is still
# valid. If it is not, the browser sign-in starts here: lumoauth for the laptop, lumoreauth for the Mini (the Mini is
# headless, so its sign-in always happens in a browser on the MacBook). A valid sign-in is left alone, and no API key
# is ever changed. Plain `darwin-rebuild switch` only prints the sign-in state (nix-modules/macos/lumo.nix); the
# activation runs as root without a desktop session and cannot hold a browser sign-in.
function darwin-reload() {
  local action="$1" host="$2"
  if [[ "$action" != (switch|build|check) || "$host" != (laptop|desktop|work) ]]; then
    echo "usage: darwin-reload <switch|build|check> <laptop|desktop|work> [darwin-rebuild arguments...]" >&2
    return 2
  fi
  shift 2
  local mini="${LUMO_MINI_USER:-havoc}@${LUMO_MINI_HOST:-macminim1.rollet.family}"
  local this="$(scutil --get LocalHostName 2>/dev/null)" remote=""
  # desktop is MacMiniM1: from any other Mac its rebuild runs there (-t: sudo asks for the password)
  [[ "$host" == desktop && "${this:l}" != macminim1 ]] && remote="$mini"
  local -a sudo_cmd
  [[ "$action" == build ]] || sudo_cmd=(sudo)   # switch and check must run as root (darwin-rebuild refuses otherwise)
  local -a fresh=()
  [[ "$action" == switch ]] && fresh=(--refresh --no-write-lock-file --override-input nixpkgs github:NixOS/nixpkgs/nixpkgs-unstable --override-input nix-darwin github:LnL7/nix-darwin --override-input nix-homebrew github:zhaofengli-wip/nix-homebrew)
  if [[ -n "$remote" ]]; then
    ssh -t "$remote" "${sudo_cmd[*]} darwin-rebuild $action --flake ~/nix-darwin#macos_desktop ${(j: :)fresh} ${(j: :)${(q)@}}" || return $?
  else
    nix-recover || return $?
    "${sudo_cmd[@]}" darwin-rebuild "$action" --flake "$HOME/nix-darwin#macos_$host" "${fresh[@]}" "$@" || return $?
  fi
  if [[ "$action" == switch ]]; then
    local rc=0
    if [[ -n "$remote" ]]; then
      local upg_status=$(ssh -n -o BatchMode=yes "$remote" cat '~/.cache/darwin-upgrade-status' 2>/dev/null)
    else
      local upg_status=$(cat ~/.cache/darwin-upgrade-status 2>/dev/null)
    fi
    if [[ -n "$upg_status" && "$upg_status" == failed:* ]]; then
      echo "darwin-reload: package upgrades failed ($upg_status); rerun: bash ~/nix-darwin/scripts/upgrade-all.sh" >&2
      rc=1
    fi
    if [[ "$host" != work ]]; then
      _lumo_signin_if_invalid "$host" "$remote"
    fi
    return $rc
  fi
  return 0
}

