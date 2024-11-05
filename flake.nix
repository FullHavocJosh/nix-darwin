{
  description = "macOS Darwin Nix Configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    nix-darwin.url = "github:LnL7/nix-darwin";
    # nix-darwin.inputs.nixpkgs.follows = "nixpkgs";
    # Adds homebrew support into nix
    nix-homebrew.url = "github:zhaofengli-wip/nix-homebrew";
  };

  outputs = inputs@{ self, nix-darwin, nixpkgs, nix-homebrew }:
  let
    globalConfigModule = { pkgs, config, ... }: {
      nixpkgs.config.allowUnfree = true;
      nixpkgs.hostPlatform = "aarch64-darwin";
      # Auto upgrade nix package and the daemon service
      services.nix-daemon.enable = true;
      # Necessary for using flakes on this system
      nix.settings.experimental-features = "nix-command flakes";
      # Create /etc/zshrc that loads the nix-services environment
      programs.zsh.enable = true;
      system.stateVersion = 5;

      fonts.packages = [
        (pkgs.nerdfonts.override { fonts = [ "JetBrainsMono" ]; })
      ];
    };

    # List packages installed in system profile. To search by name, run:
    # $ nix-env -qaP | grep wget
    # or search.nixos.org
    globalPackagesModule = { pkgs, config, ... }: {
      environment.systemPackages = with pkgs; [
        atuin
        btop
        eza
        fzf
        mkalias
        powershell
        skhd
        speedtest-cli
        stow
        tfswitch
        terraform
        terraformer
        terraforming
        terraform-inventory
        tldr
        tmux
        yabai
        zplug
      ];
    };

    macosPackagesModule_personal = { pkgs, config, ... }: {
      homebrew = {
        enable = true;
        # Install Brew Formulas
        brews = [
          "ansible"
          "ansible-lint"
          "go"
          "mas"
          "oh-my-posh"
          "prettier"
          "python3"
          "syncthing"
          "telnet"
          "tmuxinator"
          "tmuxinator-completion"
          "wireguard-go"
        ];
        # Install Brew Casks
        casks = [
          "arc"
          "alacritty"
          "battle-net"
          "balenaetcher"
          "betterdisplay"
          "curseforge"
          "discord"
          "firefox"
          "goland"
          "stats"
          "iterm2"
          "jetbrains-toolbox"
          "krita"
          "obsidian"
          "plex"
          "plexamp"
          "proton-drive"
          "protonvpn"
          "proton-pass"
          "proton-mail"
          "shottr"
          "steam"
          "sublime-text"
          "telegram-desktop"
          "the-unarchiver"
          "ultimaker-cura"
          "vanilla"
          "via"
          "vial"
          "vlc"
          "whisky"
          "google-chrome"
        ];
        # Install App Store Apps, search for ID with "mas search "
        # You must be logged into the Apps Store, and you must have purchased the app
        masApps = {
          "Noir for Safari" = 1592917505;
          "Proton Pass for Safari" = 6502835663;
          "SponsorBlock for Safari" = 1573461917;
          "Xcode" = 497799835;
        };
        # This Setting will REMOVE apps that are installed by homebrew outside of this config
        onActivation.cleanup = "zap";
        # These Settings will perform "brew update" & "brew upgrade" when services-rebuild is run
        onActivation.autoUpdate = true;
        onActivation.upgrade = true;
      };
    };

    macosConfigModule_personal = { pkgs, config, ... }: {
      system.activationScripts.applications.text = let
        env = pkgs.buildEnv {
          name = "system-applications";
          paths = config.environment.systemPackages;
          pathsToLink = "/Applications";
        };
      in pkgs.lib.mkForce ''
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

      system.activationScripts.script.text = ''
        echo "Stowing dotfiles..."
        cd /Users/havoc/nix-darwin || { echo "Failed to cd into ~/nix-darwin/dotfiles"; exit 1; }
        echo "Stowing $dir..."
        ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow ."; exit 1; }
      '';

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
        # Apps installed via nix package must include ${pkgs.APPNAME}
        dock.persistent-apps = [
          "/Applications/Alacritty.app"
          "/Applications/GoLand.app"
          "/System/Cryptexes/App/System/Applications/Safari.app"
          "/System/Applications/Music.app"
          "/Applications/Obsidian.app"
          "/System/Applications/Freeform.app"
          "/Applications/Discord.app"
          "/System/Applications/Messages.app"
          "/Applications/Telegram Desktop.app"
          "/Applications/Proton Mail.app"
          "/Applications/Proton Pass.app"
        ];
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
    };

    macosPackagesModule_work = { pkgs, config, ... }: {
      homebrew = {
        enable = true;
        # Install Brew Formulas
        brews = [
          "ansible"
          "ansible-lint"
          "go"
          "mas"
          "oh-my-posh"
          "prettier"
          "python3"
          "syncthing"
          "telnet"
          "tmuxinator"
          "tmuxinator-completion"
        ];
        # Install Brew Casks
        casks = [
          "arc"
          "alacritty"
          "balenaetcher"
          "betterdisplay"
          "citrix-workspace"
          "firefox"
          "goland"
          "iterm2"
          "jetbrains-toolbox"
          "krita"
          "plexamp"
          "proton-pass"
          "remote-desktop-manager-free"
          "shottr"
          "stats"
          "sublime-text"
          "the-unarchiver"
          "vanilla"
          "via"
          "vial"
          "vlc"
        ];
        # Install App Store Apps, search for ID with "mas search "
        # You must be logged into the Apps Store, and you must have purchased the app
        masApps = {
          "VMware Remote Console" = 1230249825;
          "Xcode" = 497799835;
        };
        # This Setting will REMOVE apps that are installed by homebrew outside of this config
        onActivation.cleanup = "zap";
        # These Settings will perform "brew update" & "brew upgrade" when services-rebuild is run
        onActivation.autoUpdate = true;
        onActivation.upgrade = true;
      };
    };

    macosConfigModule_work = { pkgs, config, ... }: {
      system.activationScripts.applications.text = let
        env = pkgs.buildEnv {
          name = "system-applications";
          paths = config.environment.systemPackages;
          pathsToLink = "/Applications";
        };
      in pkgs.lib.mkForce ''
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
        system.activationScripts.script.text = ''
          echo "Stowing dotfiles..."
          cd /Users/jrollet/nix-darwin || { echo "Failed to cd into ~/nix-darwin/dotfiles"; exit 1; }
          echo "Stowing $dir..."
          ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow ."; exit 1; }
        '';
      # System Settings for macOS
      # Documentation at: mynixos.com and look for nix-services
      system.defaults = {
        dock.autohide = false;
        dock.tilesize = 24;
        dock.largesize = 64;
        dock.mineffect = "genie";
        dock.mru-spaces = false;
        dock.showhidden = true;
        dock.launchanim = true;
        dock.orientation = "bottom";
        dock.static-only = false;
        dock.show-recents = false;
        dock.magnification = true;
        # Apps installed via nix package must include ${pkgs.APPNAME}
        dock.persistent-apps = [
          "/Applications/Alacritty.app"
          "/Applications/GoLand.app"
          "/Applications/Arc.app"
          "/Applications/Sublime Text.app"
          "/Applications/Remote Desktop Manager Free.app"
          "/Applications/Slack.app"
          "/Applications/Microsoft Outlook.app"
          "/System/Applications/Passwords.app"
          "/Applications/Cisco AnyConnect Secure Mobility Client.app"
        ];
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
    };
  in {
    darwinConfigurations."macos_personal" = nix-darwin.lib.darwinSystem {
      modules = [
        globalConfigModule
        globalPackagesModule
        macosPackagesModule_personal
        macosConfigModule_personal
        nix-homebrew.darwinModules.nix-homebrew
        ./services/yabai.nix
        ./services/skhd.nix
      ];
    };

    darwinConfigurations."macos_work" = nix-darwin.lib.darwinSystem {
      modules = [
        globalConfigModule
        globalPackagesModule
        macosPackagesModule_work
        macosConfigModule_work
        nix-homebrew.darwinModules.nix-homebrew
        ./services/yabai.nix
        ./services/skhd.nix
      ];
    };

    darwinPackagesPersonal = self.darwinConfigurations."macos_personal".pkgs;
    darwinPackagesWork = self.darwinConfigurations."macos_work".pkgs;
  };
}
