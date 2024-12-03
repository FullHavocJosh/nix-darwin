{ pkgs, config, ... }: {

  #######################################
  ### MacOS Settings for Work Devices ###
  #######################################

  system.activationScripts.script.text = ''
    echo "Stowing dotfiles..."
    cd /Users/jrollet/nix-darwin || { echo "Failed to cd into ~/nix-darwin/dotfiles"; exit 1; }
    echo "Stowing $dir..."
    ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow ."; exit 1; }
  '';
  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    # Apps installed via nix package must include ${pkgs.APPNAME}
    dock.persistent-apps = [
      "/Applications/Alacritty.app"
      "/Applications/Zen Browser.app"
      "/Applications/Sublime Text.app"
      "/Applications/Remote Desktop Manager Free.app"
      "/Applications/Slack.app"
      "/Applications/Microsoft Outlook.app"
      "/Applications/Proton Pass.app"
      "/Applications/Cisco/Cisco AnyConnect Secure Mobility Client.app"
    ];
  };
  homebrew = {
    enable = true;
    taps = [
      "warrensbox/tap"
    ];
    # Install Brew Formulas
    brews = [ ];
    # Install Brew Casks
    casks = [
      "bettermouse"
      "citrix-workspace"
      "remote-desktop-manager-free"
    ];
    # Install App Store Apps, search for ID with "mas search "
    # You must be logged into the Apps Store, and you must have purchased the app
    masApps = {
      "VMware Remote Console" = 1230249825;
      "Xcode" = 497799835;
    };
  };
}
