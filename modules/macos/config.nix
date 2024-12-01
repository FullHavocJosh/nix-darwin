{ pkgs, config, lib, ... }: {

  ##################################################
  ### Configurations Shared Across MacOS Devices ###
  ##################################################

  nixpkgs.config.allowUnfree = true;
  nixpkgs.hostPlatform = "aarch64-darwin";
  # Auto upgrade nix package and the daemon service
  services.nix-daemon.enable = true;
  # Necessary for using flakes on this system
  nix.settings.experimental-features = "nix-command flakes";
  # Create /etc/zshrc that loads the nix-services environment
  programs.zsh.enable = true;
  system.stateVersion = 5;
  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    dock.autohide = true;
    dock.tilesize = 32;
    dock.largesize = 64;
    dock.mineffect = "genie";
    dock.mru-spaces = false;
    dock.showhidden = true;
    dock.launchanim = true;
    dock.orientation = "bottom";
    dock.static-only = false;
    dock.show-recents = false;
    dock.magnification = true;
    dock.autohide-delay = 0.05;
    dock.autohide-time-modifier = 0.05;
    dock.persistent-others =
    [
      "/Applications"
    ];
    dock.wvous-bl-corner = 1;
    dock.wvous-br-corner = 1;
    dock.wvous-tl-corner = 2;
    dock.wvous-tr-corner = 1;
    dock.slow-motion-allowed = false;
    dock.dashboard-in-overlay = true;
    dock.expose-group-by-app = false;
    dock.expose-animation-duration = 0.05;
    dock.minimize-to-application = false;
    menuExtraClock.IsAnalog = false;
    menuExtraClock.ShowAMPM = false;
    menuExtraClock.ShowDate = 0;
    menuExtraClock.Show24Hour = false;
    menuExtraClock.ShowSeconds = false;
    menuExtraClock.ShowDayOfWeek = false;
    finder.ShowPathbar = true;
    finder.QuitMenuItem = false;
    finder.CreateDesktop = false;
    finder.ShowStatusBar = true;
    finder.AppleShowAllFiles = true;
    finder.FXPreferredViewStyle = "clmv";
    finder._FXSortFoldersFirst = true;
    finder.AppleShowAllExtensions = true;
    finder._FXShowPosixPathInTitle = true;
    finder.FXDefaultSearchScope = "SCcf";
    finder.FXEnableExtensionChangeWarning = false;
    loginwindow.GuestEnabled = false;
    trackpad.TrackpadThreeFingerDrag = true;
    trackpad.TrackpadThreeFingerTapGesture = 0;
    WindowManager.AutoHide = true;
    WindowManager.StandardHideDesktopIcons = true;
    WindowManager.HideDesktop = true;
    WindowManager.EnableStandardClickToShowDesktop = false;
    WindowManager.GloballyEnabled = false;
    WindowManager.AppWindowGroupingBehavior = false;
    NSGlobalDomain.AppleInterfaceStyle = "Dark";
    NSGlobalDomain.KeyRepeat = 2;
    NSGlobalDomain.InitialKeyRepeat = 10;
    NSGlobalDomain.AppleShowAllFiles = true;
    NSGlobalDomain.NSWindowResizeTime = 0.05;
    NSGlobalDomain.AppleShowAllExtensions = true;
    NSGlobalDomain.ApplePressAndHoldEnabled = false;
    NSGlobalDomain.NSScrollAnimationEnabled = true;
    NSGlobalDomain.NSDocumentSaveNewDocumentsToCloud = true;
    NSGlobalDomain.NSAutomaticInlinePredictionEnabled = false;
    NSGlobalDomain.NSAutomaticSpellingCorrectionEnabled = false;
    NSGlobalDomain.NSAutomaticPeriodSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticCapitalizationEnabled = false;
    NSGlobalDomain.NSAutomaticDashSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticQuoteSubstitutionEnabled = false;
    NSGlobalDomain.NSWindowShouldDragOnGesture = true;
    NSGlobalDomain.AppleScrollerPagingBehavior = true;
    NSGlobalDomain."com.apple.keyboard.fnState" = true;
    universalaccess.mouseDriverCursorSize = 1.25;
  };
  fonts.packages = [
    (pkgs.nerdfonts.override { fonts = [ "JetBrainsMono" ]; })
  ];
  system.activationScripts.applications.text =
    let
      env = pkgs.buildEnv {
        name = "system-applications";
        paths = config.environment.systemPackages;
        pathsToLink = "/Applications";
      };
    in
    pkgs.lib.mkForce ''
      echo "setting up /Applications..." >&2
      rm -rf /Applications/Nix\ Apps
      mkdir -p /Applications/Nix\ Apps
      find ${env}/Applications -maxdepth 1 -type l -exec readlink '{}' + |
      while read src; do
        app_name=$(basename "$src")
        echo "copying $src" >&2
        ${pkgs.mkalias}/bin/mkalias "$src" "/Applications/Nix Apps/$app_name"
      done
    '';
}
