{
  description = "Nix Configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    nix-darwin.url = "github:LnL7/nix-darwin";
    nix-darwin.inputs.nixpkgs.follows = "nixpkgs";
    nix-homebrew.url = "github:zhaofengli-wip/nix-homebrew";
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      nix-darwin,
      nix-homebrew,
      ...
    }:
    {
      darwinConfigurations."macos_laptop" = nix-darwin.lib.darwinSystem {
        specialArgs = {
          username = "havoc";
        };
        modules = [
          ./nix-modules/macos/packages.nix
          ./nix-modules/macos/config.nix
          ./nix-modules/macos/personal.nix
          nix-homebrew.darwinModules.nix-homebrew
        ];
      };
      darwinConfigurations."macos_desktop" = nix-darwin.lib.darwinSystem {
        specialArgs = {
          username = "havoc";
        };
        modules = [
          ./nix-modules/macos/packages.nix
          ./nix-modules/macos/config.nix
          ./nix-modules/macos/personal.nix
          ./nix-modules/macos/llamacpp.nix
          ./nix-modules/macos/openchamber.nix
          ./nix-modules/macos/sillytavern.nix
          nix-homebrew.darwinModules.nix-homebrew
        ];
      };
      darwinConfigurations."macos_work" = nix-darwin.lib.darwinSystem {
        specialArgs = {
          username = "jrollet";
        };
        modules = [
          ./nix-modules/macos/packages.nix
          ./nix-modules/macos/config.nix
          ./nix-modules/macos/work.nix
          nix-homebrew.darwinModules.nix-homebrew
        ];
      };
    };
}
