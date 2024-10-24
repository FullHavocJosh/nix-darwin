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
                pkgs.atuin
                pkgs.btop
                pkgs.eza
                pkgs.fzf
		pkgs.mkalias
                pkgs.neovim
                pkgs.powershell
                # pkgs.rpi-imager BROKEN?
                pkgs.skhd
                pkgs.speedtest-cli
                pkgs.stow
		pkgs.tfswitch
                pkgs.terraform
	 	pkgs.terraformer
		pkgs.terraforming
		pkgs.terraform-inventory
                pkgs.tldr
                pkgs.yabai
		pkgs.zplug
            ];

        homebrew = {
            enable = true;
            # Install Brew Apps
            brews = [
		"ansible"
		"ansible-lint"
		"go"
                "mas"
		"openconnect"
		"python3"
		"syncthing"
                "telnet"
		"wireguard-go"
            ];
            # Install Brew Casks
            casks = [
		"arc"
		"alacritty"
		"audio-hijack"
                "battle-net"
                "balenaetcher"
                "betterdisplay"
                "cinder"
		"citrix-workspace"
		"curseforge"
		"discord"
		"goland"
		"iterm2"
		"openconnect-gui"
		"jetbrains-toolbox"
		"krita"
		"librewolf"
		"obsidian"
		"plex"
		"plexamp"
		"proton-drive"
                "protonvpn"
                "proton-pass"
                "proton-mail"
                "remote-desktop-manager-free"
		"shottr"
		"slack"
		"steam"
		"sublime-text"
		"telegram-desktop"
                "the-unarchiver"
                "ultimaker-cura"
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
            # These Settings will perform "brew update" & "brew upgrade" when darwin-rebuild is run
            onActivation.autoUpdate = true;
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
            "/Applications/iTerm.app"
            "/Applications/GoLand.app"
            "/System/Cryptexes/App/System/Applications/Safari.app"
            "/Applications/Obsidian.app"
            "/System/Applications/Freeform.app"
            "/Applications/Proton Pass.app"
            "/Applications/Proton Mail.app"
            "/Applications/Discord.app"
            "/System/Applications/Messages.app"
            "/Applications/Telegram Desktop.app"
            "/System/Applications/Music.app"
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
