# Prints $1 without attribution lines and notes what it removed on stderr. Use as x=$(_strip_agent_attribution "$x"):
# the command substitution also drops the blank lines a removed footer leaves at the end.
function _strip_agent_attribution() {
  local removed
  removed=$(printf '%s\n' "$1" | grep -iE "$_AGENT_ATTRIBUTION_RE")
  if [[ -n "$removed" ]]; then
    echo "ℹ Removed agent attribution:" >&2
    printf '    %s\n' "${(@f)removed}" >&2
  fi
  printf '%s\n' "$1" | grep -viE "$_AGENT_ATTRIBUTION_RE"
}

