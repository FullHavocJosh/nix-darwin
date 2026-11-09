# TUI/CLI packages shared across ALL profiles (laptop, desktop, work)
# GUI applications are in packages-gui.nix (laptop only)
#
# PACKAGE POLICY: Prefer Homebrew for all new packages (brews/casks below).
# Only use environment.systemPackages for packages not available on Homebrew.
{
  pkgs,
  lib,
  username,
  ...
}:
let
  claudeSetup = import ./claude-setup { inherit pkgs lib username; };
in
{
  # Packages not available on Homebrew — add here only as a last resort.
  environment.systemPackages = with pkgs; [
    nil
    nixd
  ];

  homebrew = {
    enable = true;
    # The package lists are plain lists in homebrew/: a module of their own would
    # reorder them against the other modules' lists.
    taps = import ./homebrew/taps.nix;
    brews = import ./homebrew/brews.nix;
    casks = import ./homebrew/casks.nix;
    masApps = { };
    onActivation.cleanup = "none";
    onActivation.extraFlags = [ "--force" ];
    onActivation.autoUpdate = true;
    onActivation.upgrade = true;
    # casks that update themselves or are :latest are skipped by brew upgrade without this
    greedyCasks = true;
  };

  # Runs before brew bundle so Homebrew can link without conflict.
  system.activationScripts.homebrew.text = lib.mkBefore ''
    if [ -L /opt/homebrew/bin/jsonlint ] && readlink /opt/homebrew/bin/jsonlint | grep -q node_modules; then
      echo "Removing npm-installed jsonlint symlink (replaced by Homebrew)..."
      rm -f /opt/homebrew/bin/jsonlint
    fi
  '';

  # Was "packagesUserConfig" -- a name nix-darwin's own activation-scripts.nix
  # never references (its system.activationScripts.script.text hardcodes a
  # fixed list of known names: checks, groups, users, homebrew,
  # postActivation, etc). types.attrsOf submodule happily accepts any
  # attribute name, including ones nothing consumes, so this evaluated fine
  # and `nix eval` on it showed the right content, but it was never part of
  # config.system.build.toplevel's actual closure -- confirmed by comparing
  # .drvPath across commits: editing this text never changed the derivation,
  # while editing system.activationScripts.homebrew.text (a real, referenced
  # name) always did. Every darwin-rebuild switch has silently no-op'd this
  # whole block since it was introduced -- claudeTuiSetup, the Opcode
  # auto-install, and now token-optimization-setup never actually ran.
  # postActivation IS one of the real names (nix-darwin's own doc comment on
  # it: "Extra activation scripts, that can be customized by users").
  system.activationScripts.postActivation.text = lib.mkAfter claudeSetup;
}
