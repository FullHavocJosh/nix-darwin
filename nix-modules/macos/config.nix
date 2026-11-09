# System configuration, split by purpose under config/. A new file goes in the imports list.
# The core settings stay here, not in an imported file: moving them reorders merged options.
{ ... }:
{
  imports = [
    ./config/homebrew-tap-trust.nix
    ./config/gui-path.nix
    ./config/activation
    ./config/defaults.nix
    ./config/firewall.nix
  ];

  nixpkgs.config.allowUnfree = true;
  nixpkgs.hostPlatform = "aarch64-darwin";
  nix.settings.experimental-features = "nix-command flakes";
  programs.zsh.enable = true;
  system.stateVersion = 5;

  security.pam.services.sudo_local.touchIdAuth = true;
  security.sudo.extraConfig = ''
    Defaults timestamp_timeout=60
  '';
}
