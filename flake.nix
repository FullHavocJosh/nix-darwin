{
    description = "macOS Darwin Nix Configuration";
    # todo:
        # KDE config https://github.com/nix-community/plasma-manager/blob/trunk/modules/panels.nix

    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
        nix-darwin.url = "github:LnL7/nix-darwin";
        nix-darwin.inputs.nixpkgs.follows = "nixpkgs";
        # Adds homebrew support into nix
        nix-homebrew.url = "github:zhaofengli-wip/nix-homebrew";
    };

    outputs = inputs@{ self, nix-darwin, nixpkgs, nix-homebrew }:
    let
        configuration = { pkgs, config, ... }: {

            nixpkgs.config.allowUnfree = true;

            # List packages installed in system profile. To search by name, run:
            # $ nix-env -qaP | grep wget
            # or search.nixos.org
            environment.systemPackages =
            [
                # pkgs.arc-browser
                # pkgs.alacritty
                # kgs.ansible-core
                # pkgs.atuin
                # pkgs.btop
                # pkgs.cider
                # pkgs.citrix-workspace
                # pkgs.discord
                # pkgs.eza
                # pkgs.firefox
                # pkgs.fzf
                # pkhs.go
                # pkgs.goland
                # pkgs.globalprotect-openconnect
                # pkgs.iterm2
                # pkgs.jetbrains-toolbox
                # pkgs.krita
                # pkgs.mkalias
                # pkgs.neovim
                # pkgs.obsidian
                # pkgs.openconnect
                # pkgs.plexamp
                # pkgs.plex-media-player
                # pkgs.powershell
                # pkgs.python3
                # pkgs.rpi-imager
                # pkgs.skhd
                # pkgs.slack
                # pkgs.speedtest-cli
                # pkgs.steam
                # pkgs.sublimetext
                # pkgs.tfswitch
                # pkgs.terraform
                # pkgs.telegram-desktop
                # pkgs.tldr
                # pkgs.via
                # pkgs.vial
                # pkgs.vlc
                # pkgs.wireguard-go
                # pkgs.yabai
            ];

        homebrew = {
            enable = true;
            # Install Brew Apps
            brews = [
                # "syncthing"
                # "mas"
                # "telnet"
            ];
            # Install Brew Casks
            casks = [
                # "audio-hijack"
                # "battle-net"
                # "balenaetcher"
                # "betterdisplay"
                # "curseforge"
                # "proton-drive"
                # "protonvpn"
                # "proton-pass"
                # "proton-mail"
                # "remote-desktop-manager-free"
                # "the-unarchiver"
                # "curseforge"
                # "shottr"
                # "ultimaker-cura"
                # "vanilla"
            ];
            # Install App Store Apps, search for ID with "mas search "
            # You must be logged into the Apps Store, and you must have purchased the app
            masApps = {
                # "VMware Remote Console" = 1230249825;
                # "Xcode" = 497799835;
            };
            # This Setting will REMOVE apps that are installed by homebrew outside of this config
            onActivation.cleanup = "zap";
            # These Settings will perform "brew update" & "brew upgrade" when darwin-rebuild is run
            onActivation.autoUpgrade = true;
            onActivation.upgrade = true;
        };

        fonts.packages = [
            (pkgs.nerdfonts.override { fonts = [ "JetBrainsMono" ]; })
        ];

        system.activationScripts.applications.text = let
            env = pkgs.buildEnv {
                name = "system-applications";
                paths = config.environment.systemPackages;
                pathsToLink = "/Applications";
            };
        in
            pkgs.lib.mkForce ''
                # Set up applications.
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

    # System Settings for macOS
    # Documentation at: mynixos.com and look for nix-darwin
    system.defaults = {
        dock.autohide = true;
        dock.tilesize = 48;
        dock.mineffect = "genie";
        dock.mru-spaces = false;
        dock.show-recents = false;
        dock.autohide-delay = 0.05;
        dock.wvous-tl-corner = 2;
        dock.expose-animation-duration = 0.05;
        # Apps installed via nix package must include ${pkgs.APPNAME}
        dock.persistent-apps = [
            "/Applications/Finder.app"
            # "${pkgs.obsidian}/Applications/iTerm.app"
            # "${pkgs.obsidian}/Applications/GoLand.app"
            "/Applications/Safari.app"
            # "${pkgs.obsidian}/Applications/Obsidian.app"
            "/Applications/Freeform.app"
            # "/Applications/Proton Pass.app"
            # "/Applications/Proton Mail.app"
            # "${pkgs.obsidian}/Applications/Discord.app"
            "/Applications/Messages.app"
            # "${pkgs.obsidian}/Applications/Telegram Lite.app"
            "/Applications/Music.app"
        ];
        finder.FXPreferredViewStyle = "clmv";
        finder._FXSortFoldersFirst = true;
        finder.ShowPathbar = true;
        finder.CreateDesktop = false;
        finder.AppleShowAllExtensions = true;
        finder._FXShowPosixPathInTitle = true;
        loginwindow.GuestEnabled  = false;
        NSGlobalDomain.AppleInterfaceStyle = "Dark";
        trackpad.FirstClickThreshold = 2;
        trackpad.TrackpadThreeFingerDrag = true;
        WindowManager.StandardHideDesktopIcons = true;
        WindowManager.EnableStandardClickToShowDesktop = false;
        SoftwareUpdate.AutomaticallyInstallMacOSUpdates = true;
        NSGlobalDomain.NSDocumentSaveNewDocumentsToCloud = true;
        NSGlobalDomain.NSAutomaticInlinePredictionEnabled = false;
        NSGlobalDomain.NSAutomaticSpellingCorrectionEnabled = false;
        NSGlobalDomain.NSAutomaticPeriodSubstitutionEnabled = false;
        universalaccess.mouseDriverCursorSize = 1.25;
    };

    # Auto upgrade nix package and the daemon service.
    services.nix-daemon.enable = true;
    # nix.package = pkgs.nix;

    # Necessary for using flakes on this system.
    nix.settings.experimental-features = "nix-command flakes";

    # Create /etc/zshrc that loads the nix-darwin environment.
    programs.zsh.enable = true;  # default shell on catalina
    # programs.fish.enable = true;

    # Set Git commit hash for darwin-version.
    system.configurationRevision = self.rev or self.dirtyRev or null;

    # Used for backwards compatibility, please read the changelog before changing.
    # $ darwin-rebuild changelog
    system.stateVersion = 4;

    # The platform the configuration will be used on.
    nixpkgs.hostPlatform = "aarch64-darwin";
};
in
{
    # Build darwin flake using:
    # $ darwin-rebuild build --flake .#simple
    darwinConfigurations."macos" = nix-darwin.lib.darwinSystem {
        modules = [
            configuration
            nix-homebrew.darwinModules.nix-homebrew
            {
                nix-homebrew = {
                    enable = true;
                    enableRosetta = true;
                    # User owning the Homebrew prefix
                    user = "havoc";
                    autoMigrate = true;
                };
            }
        ];
    };

    # Expose the package set, including overlays, for convenience.
    darwinPackages = self.darwinConfigurations."macos".pkgs;
    };
}
