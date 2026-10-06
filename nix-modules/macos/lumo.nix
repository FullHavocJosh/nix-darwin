{ lib, ... }:
let
  home = "/Users/havoc";

  # The scripts in .config/lumo run from the nix store, so a rebuild swaps them atomically
  # and the daemons never depend on when stow runs. (The same directory is also stowed to
  # ~/.config/lumo for manual use, e.g. `zsh ~/.config/lumo/watchdog.sh`.)
  lumoSrc = ../../.config/lumo;

  # lumo-tamer is third-party and unofficial: pin the exact commit that was reviewed and tested.
  tamerRev = "0ef587b7f3d5d5165914602f0cc79bdfe7ee4e30"; # 2026-09-23

  logs = "${home}/Library/Logs";
  daemon = script: log: {
    ProgramArguments = [
      "/bin/zsh"
      "${lumoSrc}/${script}"
    ];
    UserName = "havoc";
    EnvironmentVariables = {
      HOME = home;
    };
    RunAtLoad = true;
    StandardOutPath = "${logs}/${log}";
    StandardErrorPath = "${logs}/${log}";
  };
in
{
  # Tier 0 of aistack: Lumo (Proton) as a cloud, tool-less planner. Desktop (MacMiniM1) only,
  # because it is the always-on host. Three LaunchDaemons running as havoc (no login needed):
  #   lumo-tamer    lumo-tamer's OpenAI-compatible server for Lumo (port 3003, API key protected)
  #   lumo-planner  proxy in front of it that lets Lumo ask for repo files (port 8765)
  #   lumo-watchdog every 5 min: auth/server health, ntfy alert, optional headless re-auth
  # Secrets live in Doppler FullHavocJosh/root_macmini; see .config/lumo/*.sh for the names.
  # Interactive Proton login cannot be declarative: run `tamer auth browser` once (README).

  # Only the optional headless re-auth in watchdog.sh uses it (the laptop gets it from packages-gui.nix).
  homebrew.casks = [ "ungoogled-chromium" ];

  system.activationScripts.lumoTamerProvision.text = lib.mkAfter ''
    sudo -u havoc HOME=${home} bash -c '(nohup /bin/zsh ${lumoSrc}/provision-tamer.sh ${tamerRev} </dev/null >/dev/null 2>&1 &)'
    echo "[lumo-tamer-provisioner] check running in background -- tail ${home}/lumo-tamer.provision.log"
  '';

  launchd.daemons.lumo-tamer.serviceConfig = daemon "run-tamer.sh" "lumo-tamer.log" // {
    KeepAlive = true;
    ThrottleInterval = 10;
  };

  launchd.daemons.lumo-planner.serviceConfig = daemon "run-planner.sh" "lumo-planner.log" // {
    KeepAlive = true;
    ThrottleInterval = 10;
  };

  launchd.daemons.lumo-watchdog.serviceConfig = daemon "watchdog.sh" "lumo-watchdog.log" // {
    StartInterval = 300;
  };
}
