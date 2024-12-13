{ pkgs, lib, ... }: {

  ##################################################
  ### Configurations Shared Across MacOS Devices ###
  ##################################################

  home.stateVersion = "23.05"; # Set to your Nixpkgs stable release version
  home.username = "havoc";    # Set the username
  home.homeDirectory = "/home/havoc"; # Set the home directory
  programs.home-manager.enable = true;

  programs.zsh = {
    enable = true;
    oh-my-zsh = {
      enable = true;
      theme = "agnoster";
    };
  };
  services.syncthing.enable = false;
  # Activation script to run stow.sh
  home.activation = {
    text = ''
      echo "Running stow.sh for Fedora configuration..."
      /home/havoc/nix-darwin/.scripts/stow.sh
    '';
  };
}
