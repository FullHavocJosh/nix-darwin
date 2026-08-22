{ pkgs, ... }:
{
  networking.hostName = "MacBookM2Pro";
  networking.computerName = "MacBookM2Pro";

  # Remote Login, scoped to the home LAN and Tailscale tailnet only -- the
  # laptop travels to untrusted networks, so SSH must stay closed everywhere
  # else. macminim1 needs to reach this machine to converge
  # infrastructure-context.json (see personal.nix's sync activation script).
  services.openssh = {
    enable = true;
    extraConfig = ''
      Match Address 192.168.144.0/24,100.64.0.0/10,fd7a:115c:a1e0::/48
        AllowUsers havoc

      Match Address *,!192.168.144.0/24,!100.64.0.0/10,!fd7a:115c:a1e0::/48
        DenyUsers *
    '';
  };
}
