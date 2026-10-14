# Applies the Time Machine exclusion list from the repo root
# (nix-darwin/timemachine-exclusions.txt) to every profile that imports
# config.nix. The list is the single source of truth:
# scripts/check-timemachine-exclusions.sh validates it, this module applies it.
{ config, lib, ... }:
let
  # One path per line, '#' comment lines and blank lines dropped, surrounding
  # whitespace trimmed (the file ends with a newline, so the split leaves a
  # trailing empty entry).
  paths = lib.filter (line: line != "" && !(lib.hasPrefix "#" line)) (
    map (line: lib.trim line) (
      lib.splitString "\n" (builtins.readFile ../../timemachine-exclusions.txt)
    )
  );

  # One shell word per path for the array in the activation script below. A
  # leading '~/' becomes $USER_HOME, which the script resolves at activation
  # time: activation runs as root, where a literal ~ would be root's home.
  # escapeShellArg cannot wrap the whole word -- it single-quotes anything that
  # holds a '$', which would freeze $USER_HOME into literal text. So the prefix
  # is double-quoted and the path itself goes through escapeShellArg: returned
  # unchanged when it needs no quoting (dropped straight between the double
  # quotes), otherwise already single-quoted (concatenated onto the prefix,
  # since bash joins adjacent quoted parts into a single word).
  quoted =
    path:
    let
      rest = lib.removePrefix "~/" path;
      escaped = lib.escapeShellArg rest;
    in
    if rest == path then
      lib.escapeShellArg path
    else if escaped == rest then
      "\"$USER_HOME/${escaped}\""
    else
      "\"$USER_HOME/" + escaped;
in
{
  # Must be `postActivation` via lib.mkAfter (which merges with the other
  # modules' text): nix-darwin only embeds a hardcoded list of
  # activationScripts names in the built `activate`, so any other key evaluates
  # fine and then never runs.
  system.activationScripts.postActivation.text = lib.mkAfter ''
    # Time Machine exclusions, sticky (no -p): they are re-applied on every
    # darwin-rebuild, which is what restores them after `tmutil resetexclusions`
    # or a machine restore. Every step is non-fatal on purpose -- a directory
    # that does not exist (the list is shared by machines that do not all have
    # every cache dir), a path tmutil refuses, or tmutil missing entirely must
    # never fail the whole activation, so failures only print a warning.
    USER_NAME="${config.system.primaryUser}"
    USER_HOME=$(eval echo ~$USER_NAME)

    tm_exclusions=(
      ${lib.concatMapStringsSep "\n  " quoted paths}
    )

    tm_added=0
    for p in "''${tm_exclusions[@]}"; do
      # Nothing to exclude: the path is absent on this machine.
      if [ ! -e "$p" ]; then
        continue
      fi
      # Already excluded, nothing to do. `isexcluded` prints [Excluded] or
      # [NotExcluded]; 2>/dev/null because tmutil complains when the path is
      # not on a Time Machine capable volume.
      if /usr/bin/tmutil isexcluded "$p" 2>/dev/null | grep -q '\[Excluded\]'; then
        continue
      fi
      if /usr/bin/tmutil addexclusion "$p"; then
        tm_added=$((tm_added + 1))
      else
        echo "warning: could not exclude $p" >&2
      fi
    done
    echo "[timemachine] $tm_added exclusion(s) added from timemachine-exclusions.txt"
  '';
}
