{
  config,
  lib,
  pkgs,
  username,
  ...
}:
let
  cfg = config.local.llamaReviewerProxy;
in
{
  # Authenticated reverse proxy for the loopback-only 9B reviewer (llama-server-local, 127.0.0.1:8080), so other
  # machines on the LAN can use it. macmini (macos_desktop) only; llamacpp-local.nix is untouched and the 9B stays
  # bound to loopback.
  #
  # Why nginx: it is in nixpkgs, supports aarch64-darwin, and is a proven reverse proxy that streams responses
  # unbuffered. Why a LaunchDaemon: same as llama-server-local, it starts at boot on the headless Mini with no login.
  # The Bearer key is read at start from ~/.config/llama-reviewer/api-key by the script, so it is never in the store.
  options.local.llamaReviewerProxy = {
    enable = lib.mkEnableOption "the authenticated nginx proxy in front of the loopback 9B reviewer";
    address = lib.mkOption {
      type = lib.types.str;
      description = "LAN IPv4 address nginx binds to.";
    };
    port = lib.mkOption {
      type = lib.types.port;
      default = 8083;
      description = "Port nginx listens on.";
    };
  };

  config = lib.mkIf cfg.enable {
    # The application firewall prompts for a binary it has not seen. The rule is per store path, so it is redone at
    # each switch. Hooked on postActivation: nix-darwin drops custom activationScripts names.
    system.activationScripts.postActivation.text = lib.mkAfter ''
      /usr/libexec/ApplicationFirewall/socketfilterfw --add ${pkgs.nginx}/bin/nginx >/dev/null
      /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp ${pkgs.nginx}/bin/nginx >/dev/null
      echo "[llama-reviewer-proxy] application firewall: incoming connections allowed for ${pkgs.nginx}/bin/nginx"
    '';

    launchd.daemons.llama-reviewer-proxy = {
      serviceConfig = {
        ProgramArguments = [
          "/bin/bash"
          "${../../scripts/llama-reviewer-proxy.sh}"
        ];
        EnvironmentVariables = {
          HOME = "/Users/${username}";
          NGINX_BIN = "${pkgs.nginx}/bin/nginx";
          LISTEN_ADDR = cfg.address;
          LISTEN_PORT = toString cfg.port;
        };
        UserName = username;
        KeepAlive = true;
        RunAtLoad = true;
        ThrottleInterval = 30;
        StandardOutPath = "/tmp/llama-reviewer-proxy.log";
        StandardErrorPath = "/tmp/llama-reviewer-proxy.error.log";
      };
    };
  };
}
