# Runs the user-level setup (skills, MCP servers, stow, repo updates, tuios) at the end of every
# activation. scripts/ holds the pieces of one bash script, joined in name order: they share one
# process, so a variable set in one piece is visible to the later ones. Name a new piece with a
# number that puts it where it must run.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  fragments = import ../../lib/fragments.nix { inherit lib; };
in
{
  system.activationScripts.script.text = lib.mkAfter (
    fragments.dir ./scripts {
      coreutils = "${pkgs.coreutils}";
      primaryUserQuoted = "\"${config.system.primaryUser}\"";
      stow = "${pkgs.stow}";
    }
  );
}
