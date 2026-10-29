{
  config,
  lib,
  pkgs,
  ...
}:
let
  ensureScript = pkgs.writeShellScript "launchd-ensure" (
    builtins.readFile ../../scripts/launchd-ensure.sh
  );

  user = config.system.primaryUser;

  triple = domain: dir: d: [
    domain
    d.serviceConfig.Label
    "${dir}/${d.serviceConfig.Label}.plist"
  ];

  args = lib.concatLists (
    map (triple "system" "/Library/LaunchDaemons") (lib.attrValues config.launchd.daemons)
    ++ map (triple "gui" "/Library/LaunchAgents") (lib.attrValues config.launchd.agents)
    ++ map (triple "gui" "/Users/${user}/Library/LaunchAgents") (
      lib.attrValues config.launchd.user.agents
    )
  );
in
{
  # Must be postActivation: nix-darwin drops activationScripts names it does not know.
  system.activationScripts.postActivation.text = lib.mkAfter ''
    # nix-darwin reloads a service only when its plist changed, so one that dropped out of launchd
    # stays down across switches. Lint every managed plist and bootstrap what launchd has not loaded.
    ${ensureScript} --user ${lib.escapeShellArg user} ${lib.escapeShellArgs args} || echo "[launchd-ensure] some launchd services need attention (see above)" >&2
  '';
}
