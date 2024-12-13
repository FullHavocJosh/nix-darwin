{
  description = "Nix Configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
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
          ./nix-modules/services/skhd.nix
          ./nix-modules/services/yabai.nix
        ];
      };
      darwinConfigurations."macos_work" = nix-darwin.lib.darwinSystem {
        modules = [
          ./nix-modules/macos/packages.nix
          ./nix-modules/macos/config.nix
          ./nix-modules/macos/work.nix
          nix-homebrew.darwinModules.nix-homebrew
          ./nix-modules/services/skhd.nix
          ./nix-modules/services/yabai.nix
        ];
      };
    };
}
