{
  description = "Nix Configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/release-24.11";
    nix-darwin.url = "github:LnL7/nix-darwin";
    nix-darwin.inputs.nixpkgs.follows = "nixpkgs";
    nix-homebrew.url = "github:zhaofengli-wip/nix-homebrew";
  };

  outputs = inputs@{ self, nixpkgs, nix-darwin, nix-homebrew, ... }:
  {
    darwinConfigurations."macos_personal" = nix-darwin.lib.darwinSystem {
      modules = [
        ./nix-modules/macos/packages.nix
        ./nix-modules/macos/config.nix
        ./nix-modules/macos/personal.nix
        nix-homebrew.darwinModules.nix-homebrew
      ];
    };
    darwinConfigurations."macos_work" = nix-darwin.lib.darwinSystem {
      modules = [
        ./nix-modules/macos/packages.nix
        ./nix-modules/macos/config.nix
        ./nix-modules/macos/work.nix
        nix-homebrew.darwinModules.nix-homebrew
      ];
    };
  };
}
