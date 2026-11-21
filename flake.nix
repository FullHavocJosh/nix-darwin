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
          ./nix-modules/macos/packages-tui.nix
          ./nix-modules/macos/packages-gui.nix
          ./nix-modules/macos/packages-laptop-only.nix
          ./nix-modules/macos/packages-devtest.nix
          ./nix-modules/macos/config.nix
          ./nix-modules/macos/launchd-ensure.nix
          ./nix-modules/macos/personal.nix
          ./nix-modules/macos/laptop.nix
          ./nix-modules/macos/timemachine-exclusions.nix
          ./nix-modules/macos/llamacpp-local.nix
          ./nix-modules/macos/lumo.nix # loopback only, own keys and sign-in (local.lumo.lan defaults to false)
          ./nix-modules/macos/clipcascade.nix
          { local.clipcascade.enable = true; }
          nix-homebrew.darwinModules.nix-homebrew
        ];
      };
      darwinConfigurations."macos_desktop" = nix-darwin.lib.darwinSystem {
        specialArgs = {
          username = "havoc";
        };
        modules = [
          ./nix-modules/macos/packages-tui.nix
          ./nix-modules/macos/config.nix
          ./nix-modules/macos/launchd-ensure.nix
          ./nix-modules/macos/personal.nix
          ./nix-modules/macos/desktop.nix
          ./nix-modules/macos/timemachine-exclusions.nix
          ./nix-modules/macos/llamacpp-local.nix
          ./nix-modules/macos/lumo.nix
          { local.lumo.lan = true; } # serve Lumo to every device on the network
          ./nix-modules/macos/llama-reviewer-proxy.nix
          # the Mini has a DHCP reservation for this address
          {
            local.llamaReviewerProxy = {
              enable = true;
              address = "192.168.144.4";
            };
          }
          ./nix-modules/macos/clipcascade.nix
          { local.clipcascade.enable = true; }
          nix-homebrew.darwinModules.nix-homebrew
        ];
      };
      darwinConfigurations."macos_work" = nix-darwin.lib.darwinSystem {
        specialArgs = {
          username = "jrollet";
        };
        modules = [
          ./nix-modules/macos/packages-tui.nix
          ./nix-modules/macos/packages-gui.nix
          ./nix-modules/macos/config.nix
          ./nix-modules/macos/launchd-ensure.nix
          ./nix-modules/macos/work.nix
          ./nix-modules/macos/clipcascade.nix
          # { local.clipcascade.enable = true; } # uncomment to enable once company policy allows syncing the work clipboard to clip.rollet.family
          ./nix-modules/macos/llamacpp-local.nix
          nix-homebrew.darwinModules.nix-homebrew
        ];
      };
    };
}
