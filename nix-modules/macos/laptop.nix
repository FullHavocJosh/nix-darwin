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

  # Matches macminim1's existing ~/.ssh/authorized_keys -- once services.openssh.enable
  # is on, nix-darwin routes key lookup through /etc/ssh/nix_authorized_keys.d/havoc
  # instead of the plain authorized_keys file, so this has to be declared explicitly
  # or every inbound connection (e.g. macminim1's half of the infra-context sync in
  # personal.nix) fails with "Permission denied (publickey)".
  users.users.havoc.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGDGMODrm0bM4Y2qnYRory7xSKQq3LLSLc0J7vzLHp9r josh@rollet.family"
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIB5YgF0KwOuadZn/diOuhxot4EWWng2+IDm+b67GwCaQ josh@rollet.family"
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEibecAhZFNAfYmFwUHNCERbdEuapG4EEfd1QOg4uyDS josh@rollet.family"
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMbJZjdgBYuMnqPmiIMDBz8xbsCq/lhFVLSfFqDpy/oV josh@rollet.family"
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIqA3gKzspRERKswFA4p9ZrdOYfpVeE/52YlbF6rGv0q josh@rollet.family"
  ];

  # Mac App Store apps: only safe on hosts that get `darwin-rebuild switch`
  # run interactively from their own GUI session. `mas install`/`upgrade`
  # needs the Aqua bootstrap session to talk to the App Store daemons, and
  # hangs forever (no error, no dropped connection) when darwin-rebuild is
  # invoked over SSH -- which is how MacMiniM1 (desktop.nix) is always
  # updated. Keep masApps host-scoped here rather than in shared personal.nix.
  homebrew.masApps = {
    "Search+ for Safari" = 6781814441;
  };
}
