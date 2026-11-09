# The switch is usually typed as plain `sudo darwin-rebuild switch --flake ~/nix-darwin#macos_<host>` (often behind
# `gp && source ~/.zshrc* &&`), not through darwin-reload, so an interactive shell watches for it: preexec remembers
# the command line, precmd runs the same sign-in check once the line has finished with exit 0.
#   macos_laptop   this machine's sign-in (lumoauth when it is not valid), then the Mini's as well, because the Mini is
#                  headless and can only be signed in from here (lumoreauth when it is not valid)
#   macos_desktop  typed on the Mini itself: its sign-in; when it is not valid this prints what to run on the MacBook
# A darwin-reload command line does not contain "darwin-rebuild", so the check never runs twice.
function _lumo_switch_preexec() {
  _LUMO_SWITCH_CMD=""
  [[ "$1" == *darwin-rebuild*switch*macos_(laptop|desktop)* ]] && _LUMO_SWITCH_CMD="$1"
}
function _lumo_switch_precmd() {
  local rc=$? cmd="$_LUMO_SWITCH_CMD"
  _LUMO_SWITCH_CMD=""
  [[ -n "$cmd" && $rc -eq 0 ]] || return $rc
  if [[ "$cmd" == *macos_desktop* ]]; then
    _lumo_signin_if_invalid desktop ""
  else
    _lumo_signin_if_invalid laptop ""
    # a laptop switch starts no provisioning on the Mini, so waiting for one there would only block the prompt
    _lumo_signin_if_invalid desktop "${LUMO_MINI_USER:-havoc}@${LUMO_MINI_HOST:-macminim1.rollet.family}" nowait
  fi
  return $rc
}
if [[ -o interactive ]]; then
  autoload -Uz add-zsh-hook
  add-zsh-hook preexec _lumo_switch_preexec
  add-zsh-hook precmd _lumo_switch_precmd
  add-zsh-hook preexec _nix_recover_preexec
  # preexec runs before a command line starts. The usual line sources this file and then switches, so in a shell
  # that did not have the hook yet (or after a change to it) preexec never saw that line and the first switch was
  # skipped. $history[$HISTCMD] is the line running right now: arm the check from it as preexec would have.
  zmodload -F zsh/parameter p:history 2>/dev/null
  _lumo_switch_preexec "${history[$HISTCMD]:-}"
  _nix_recover_preexec "${history[$HISTCMD]:-}"
fi
