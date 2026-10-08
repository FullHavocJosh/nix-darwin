{ lib, config, ... }:
let
  cfg = config.local.lumo;
  home = "/Users/havoc";

  # The scripts in .config/lumo run from the nix store, so a rebuild swaps them atomically
  # and the daemons never depend on when stow runs. (The same directory is also stowed to
  # ~/.config/lumo for manual use, e.g. `zsh ~/.config/lumo/watchdog.sh`.)
  lumoSrc = ../../.config/lumo;

  # lumo-tamer is third-party and unofficial: pin the exact commit that was reviewed and tested.
  tamerRev = "0ef587b7f3d5d5165914602f0cc79bdfe7ee4e30"; # 2026-09-23

  logs = "${home}/Library/Logs";
  asHavoc = "sudo -u havoc HOME=${home} PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin";
  daemon = script: log: {
    ProgramArguments = [
      "/bin/zsh"
      "${lumoSrc}/${script}"
    ];
    UserName = "havoc";
    EnvironmentVariables = {
      HOME = home;
      # read by .config/lumo/lumo-common.sh: 1 = serve the network with Doppler's keys, 0 = loopback, own keys
      LUMO_LAN = if cfg.lan then "1" else "0";
    };
    RunAtLoad = true;
    StandardOutPath = "${logs}/${log}";
    StandardErrorPath = "${logs}/${log}";
  };
in
{
  options.local.lumo.lan = lib.mkOption {
    type = lib.types.bool;
    default = false;
    description = ''
      true (the desktop, MacMiniM1): tamer and the planner proxy serve every device on the network, protected by
      the API keys in Doppler, and the application firewall is told to let them through. The headless Mini is
      signed in from the MacBook with `lumoreauth`.
      false (the laptop): both listen on 127.0.0.1 only, the firewall is not touched, and the host has its own
      keys and its own Proton sign-in (`lumoauth`), separate from the desktop's.
    '';
  };

  config = {
    # Lumo (Proton) for aidev, on every personal Mac. Two LaunchDaemons running as havoc (no login needed):
    #   lumo-tamer    lumo-tamer's OpenAI-compatible server for Lumo (port 3003, API key protected)
    #   lumo-watchdog every 5 min: auth/server health, ntfy alert, optional headless re-auth
    # Which interfaces tamer listens on and where its keys come from depends on local.lumo.lan (above).
    # Interactive Proton login cannot be declarative: sign each host in once (README).
    # There used to be a third daemon, lumo-planner (port 8765), a proxy that answered Lumo's requests for files from
    # one fixed repository. That loop now runs inside aidev against whatever project it is started in
    # (.config/aistack/ralph_mcp.py, with .config/lumo/lumo_planner.py as a library), so the daemon is gone.

    # Only the optional headless re-auth in watchdog.sh uses it (the laptop gets it from packages-gui.nix).
    homebrew.casks = lib.mkIf cfg.lan [ "ungoogled-chromium" ];

    # nix-darwin only assembles a fixed set of activationScripts names into the activate script; a custom
    # name (the first version used lumoTamerProvision) is silently dropped, so this hooks postActivation.
    system.activationScripts.postActivation.text = lib.mkAfter (
      ''
            sudo -u havoc HOME=${home} LUMO_LAN=${if cfg.lan then "1" else "0"} bash -c '(nohup /bin/zsh ${lumoSrc}/provision-tamer.sh ${tamerRev} </dev/null >/dev/null 2>&1 &)'
            echo "[lumo-tamer-provisioner] check running in background -- tail ${home}/lumo-tamer.provision.log"

        # Sign-in state, so an expired one is noticed at the next switch and not only through the watchdog's alert.
        if [ -d ${home}/lumo-tamer/dist ]; then
          if ${asHavoc} /usr/bin/perl -e 'alarm shift; exec @ARGV' 20 /bin/sh -c 'cd ${home}/lumo-tamer && tamer auth status 2>&1' | grep -q "Authentication is configured and valid"; then
            echo "[lumo] Proton sign-in: valid"
          else
            echo "[lumo] Proton sign-in: NEEDS ATTENTION -- ${
              if cfg.lan then "run lumoreauth on the MacBook" else "run lumoauth on this machine"
            }"
          fi
        fi
      ''
      + lib.optionalString (!cfg.lan) ''
        echo "[lumo] loopback only on this host: tamer binds 127.0.0.1, no firewall rule is added"
      ''
      + lib.optionalString cfg.lan ''

        # Homebrew's Python used to be allowed through the application firewall for the lumo-planner daemon, which no
        # longer exists. Take the rule away again; this does nothing once it is gone.
        py_base=$(sudo -u havoc HOME=${home} /opt/homebrew/bin/python3 -c 'import sys; print(sys.base_prefix)' 2>/dev/null)
        py_app=$(realpath "$py_base/Resources/Python.app/Contents/MacOS/Python" 2>/dev/null)
        if [ -n "$py_app" ] && /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep -qF "$py_app"; then
          /usr/libexec/ApplicationFirewall/socketfilterfw --remove "$py_app" >/dev/null
          echo "[lumo] application firewall: removed the incoming-connections rule for $py_app (the planner daemon is gone)"
        fi

        # The macOS application firewall (enabled on the Mini) drops inbound connections to binaries it has not been
        # told to allow. Allow exactly tamer's node, so other machines can use the Mini's tamer (aidev's second
        # choice, the public gateway on the Hetzner cluster, and other home services). tamer's own
        # API key (Doppler LUMO_TAMER_API_KEY) is the only protection, so this is LAN only. Any other node program
        # that listens on the Mini becomes reachable too; none does today.
        node_bin=$(realpath "$(sudo -u havoc HOME=${home} /opt/homebrew/bin/node -p 'process.execPath' 2>/dev/null)" 2>/dev/null)
        if [ -n "$node_bin" ] && [ -x "$node_bin" ]; then
          /usr/libexec/ApplicationFirewall/socketfilterfw --add "$node_bin" >/dev/null
          /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "$node_bin" >/dev/null
          echo "[lumo-tamer] application firewall: incoming connections allowed for $node_bin"
        else
          echo "[lumo-tamer] WARNING: node not found, firewall rule not added" >&2
        fi
      ''
    );

    launchd.daemons.lumo-tamer.serviceConfig = daemon "run-tamer.sh" "lumo-tamer.log" // {
      KeepAlive = true;
      ThrottleInterval = 10;
    };

    launchd.daemons.lumo-watchdog.serviceConfig = daemon "watchdog.sh" "lumo-watchdog.log" // {
      StartInterval = 300;
    };
  };
}
