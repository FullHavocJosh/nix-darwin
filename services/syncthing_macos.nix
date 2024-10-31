{ pkgs, ... }: {
  services.syncthing = {
    enable = true;
    user = "havoc"; # Replace with your macOS username
    dataDir = "/User/havoc/"; # Default folder for new synced folders
  };
}
