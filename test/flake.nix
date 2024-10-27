{
  description = "Nix Darwin Test for systemPackages";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    nix-darwin.url = "github:LnL7/nix-darwin";
  };

  outputs = { self, nixpkgs, nix-darwin, ... }:
  {
    darwinConfigurations."macos_test" = nix-darwin.lib.darwinSystem {
      modules = [
        ({ pkgs, config, ... }: {
          nixpkgs.hostPlatform = "aarch64-darwin"; # Use "x86_64-darwin" if on Intel Mac

          environment.systemPackages = with pkgs; [
            atuin
            btop
            eza
            fzf
            stow
          ];

          services.nix-daemon.enable = true;
          nix.settings.experimental-features = "nix-command flakes";
          system.stateVersion = 5;
        })
      ];
    };
  };
}
