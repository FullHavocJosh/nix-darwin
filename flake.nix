{
  description = "Nix Configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    home-manager.url = "github:nix-community/home-manager/release-24.11";
    nix-darwin.url = "github:LnL7/nix-darwin";
    # Adds homebrew support into nix
    nix-homebrew.url = "github:zhaofengli-wip/nix-homebrew";
  };

  outputs = inputs@{ self, nixpkgs, home-manager, nix-darwin, nix-homebrew }:
    let
    in
    {
      darwinConfigurations."macos_personal" = nix-darwin.lib.darwinSystem {
        modules = [
          ./nix-modules/macos/packages.nix
          ./nix-modules/macos/config.nix
          ./nix-modules/macos/personal.nix
          nix-homebrew.darwinModules.nix-homebrew
          #./nix-modules/services/stats.nix
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
          #./nix-modules/services/stats.nix
          ./nix-modules/services/skhd.nix
          ./nix-modules/services/yabai.nix
        ];
      };
      homeConfigurations."fedora_personal" = home-manager.lib.homeManagerConfiguration {
        pkgs = inputs.nixpkgs.legacyPackages."x86_64-linux";
        modules = [
          ./nix-modules/fedora/packages.nix
          ./nix-modules/fedora/config.nix
        ];
      };
    darwinPackagesPersonal = self.darwinConfigurations."macos_personal".config.system.build.toplevel;
    darwinPackagesWork = self.darwinConfigurations."macos_work".config.system.build.toplevel;
    x86_64-linux = self.homeConfigurations."fedora_personal".activationPackage;
    };
}
