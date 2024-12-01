{
  description = "macOS Darwin Nix Configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    home-manager.url = "github:nix-community/home-manager/release-24.11";
    nix-darwin.url = "github:LnL7/nix-darwin";
    # Adds homebrew support into nix
    nix-homebrew.url = "github:zhaofengli-wip/nix-homebrew";
  };

  outputs = inputs@{ self, nixpkgs, home-manager, nix-darwin, nix-homebrew }:
    let

      ###############################################
      ### Brew Applications Shared Across Devices ###
      ###############################################

      brewPackagesModule_shared = { pkgs, config, ... }: {
        homebrew = {
          enable = true;
          taps = [
            "warrensbox/tap"
          ];
          # Install Brew Formulas
          brews = [
            "ansible"
            "ansible-lint"
            "cmake"
            "fastfetch"
            "go"
            "kanata"
            "luarocks"
            "neovim"
            "mas"
            "oh-my-posh"
            "prettier"
            "syncthing"
            "rust"
            "telnet"
            "terraform"
            "terraform-inventory"
            "terraform-ls"
            "terraform-lsp"
            "terraformer"
            "tflint"
            "tfswitch"
            "tmux"
            "tmuxinator"
            "tmuxinator-completion"
            "tpm"
            "watch"
            "bash-language-server"
            "lua-language-server"
            "yaml-language-server"
          ];
          # Install Brew Casks
          casks = [
            "alacritty"
            "balenaetcher"
            "betterdisplay"
            "google-chrome"
            "goland"
            "iterm2"
            "jetbrains-toolbox"
            "karabiner-elements"
            "krita"
            "plexamp"
            "proton-drive"
            "proton-pass"
            "shottr"
            "stats"
            "sublime-text"
            "the-unarchiver"
            "vanilla"
            "via"
            "vial"
            "vlc"
            "zen-browser"
          ];
          # This Setting will REMOVE apps that are installed by homebrew outside of this config
          onActivation.cleanup = "zap";
          # These Settings will perform "brew update" & "brew upgrade" when services-rebuild is run
          onActivation.autoUpdate = true;
          onActivation.upgrade = true;
        };
      };

      ############################################
      ### MacOS Settings Shared Across Devices ###
      ############################################

      macosPackagesModule_shared = { pkgs, config, ... }: {
        environment.systemPackages = with pkgs; [
          atuin
          btop
          eza
          fzf
          mkalias
          powershell
          python3
          skhd
          speedtest-cli
          sshpass
          stow
          tldr
          yabai
          zplug
        ];
        homebrew = {
          enable = true;
          # Install App Store Apps, search for ID with "mas search "
          # You must be logged into the Apps Store, and you must have purchased the app
          masApps = {
            "Noir for Safari" = 1592917505;
            "Xcode" = 497799835;
          };
          # These Settings will perform "brew update" & "brew upgrade" when services-rebuild is run
          onActivation.autoUpdate = true;
          onActivation.upgrade = true;
        };
      };

      macosConfigModule_shared = { pkgs, config, lib, ... }: {
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
      };

      ###########################################
      ### MacOS Settings for Personal Devices ###
      ###########################################

      macosConfigModule_personal = { pkgs, config, ... }: {
        system.activationScripts.script.text = ''
          echo "Stowing dotfiles..."
          cd /Users/havoc/nix-darwin || { echo "Failed to cd into ~/nix-darwin/dotfiles"; exit 1; }
          echo "Stowing $dir..."
          ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow ."; exit 1; }
        '';

        # System Settings for macOS
        # Documentation at: mynixos.com and look for nix-services
        system.defaults = {
          dock.persistent-apps = [
            "/Applications/Alacritty.app"
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
        };
        homebrew = {
          enable = true;
          taps = [
            "warrensbox/tap"
          ];
          # Install Brew Formulas
          brews = [
            "kanata"
            "wireguard-go"
          ];
          # Install Brew Casks
          casks = [
            "battle-net"
            "curseforge"
            "discord"
            "google-chrome"
            "obsidian"
            "plex"
            "proton-drive"
            "protonvpn"
            "proton-mail"
            "steam"
            "telegram-desktop"
            "ultimaker-cura"
            "whisky"
          ];
          # Install App Store Apps, search for ID with "mas search "
          # You must be logged into the Apps Store, and you must have purchased the app
          masApps = {
            "Proton Pass for Safari" = 6502835663;
            "SponsorBlock for Safari" = 1573461917;
          };
          # This Setting will REMOVE apps that are installed by homebrew outside of this config
          onActivation.cleanup = "zap";
          # These Settings will perform "brew update" & "brew upgrade" when services-rebuild is run
          onActivation.autoUpdate = true;
          onActivation.upgrade = true;
        };
      };

      #######################################
      ### MacOS Settings for Work Devices ###
      #######################################

      macosConfigModule_work = { pkgs, config, ... }: {
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
          brews = [];
          # Install Brew Casks
          casks = [
            "citrix-workspace"
            "remote-desktop-manager-free"
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

      #########################################
      ### Fedora Home-Manager Configuration ###
      #########################################

      fedoraConfigModule = { pkgs, lib, ... }: {
        home.stateVersion = "23.05"; # Set to your Nixpkgs stable release version
        home.username = "havoc";    # Set the username
        home.homeDirectory = "/home/havoc"; # Set the home directory

        # List of Linuxbrew packages to install
        brewPackages = [
          "ansible"
          "ansible-lint"
          "cmake"
          "fastfetch"
          "go"
          "luarocks"
          "neovim"
          "oh-my-posh"
          "prettier"
          "syncthing"
          "rust"
          "telnet"
          "tmux"
          "tmuxinator"
          "tmuxinator-completion"
          "tpm"
          "watch"
          "bash-language-server"
          "lua-language-server"
          "yaml-language-server"
          "atuin"
          "zplug"
        ];
        # List of DNF packages to install
        dnfPackages = [
          "alacritty"
          "btop"
          "git"
          "neovim"
          "vlc"
        ];
        # List of Flatpaks to install
        flatpakApps = [
          "com.discordapp.Discord"
          "com.jetbrains.GoLand"
        ];

        # Custom activation script for Linuxbrew packages
        home.activation.linuxbrewPackages = lib.mkAfter ''
          echo "Installing Linuxbrew packages..."
          eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
          brew update

          # Install formulas (brews)
          echo "Installing Brew packages..."
          ${lib.concatStringsSep "\n" (map (pkg: ''
            if ! brew list --formula | grep -q "^${pkg}$"; then
              echo "Installing ${pkg}..."
              brew install ${pkg}
            else
              echo "${pkg} is already installed."
            fi
          '') brewPackages)}

          echo "Linuxbrew packages installed successfully."
        '';

        # Add a custom activation script for DNF packages
        home.activation.dnfPackages = lib.mkAfter ''
          echo "Setting up DNF packages..."

          # Update DNF cache
          echo "Updating DNF cache..."
          sudo dnf makecache -y

          # Install DNF packages
          echo "Installing DNF packages..."
          ${lib.concatStringsSep "\n" (map (pkg: ''
            if ! rpm -q ${pkg} &> /dev/null; then
              echo "Installing ${pkg}..."
              sudo dnf install -y ${pkg}
            else
              echo "${pkg} is already installed."
            fi
          '') dnfPackages)}

          echo "DNF package setup complete."
        '';

        # Add a custom activation script for Flatpak
        home.activation.flatpakPackages = lib.mkAfter ''
          echo "Setting up Flatpak..."
          # Ensure Flatpak is installed
          if ! command -v flatpak &> /dev/null; then
            echo "Flatpak is not installed. Installing it..."
            sudo dnf install -y flatpak
          fi

          # Add Flathub repository if not already added
          if ! flatpak remotes | grep -q "flathub"; then
            echo "Adding Flathub repository..."
            flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
          fi

          # Install Flatpak applications
          echo "Installing Flatpak applications..."
          ${lib.concatStringsSep "\n" (map (app: ''
            if ! flatpak list | grep -q "${app}"; then
              echo "Installing ${app}..."
             flatpak install -y flathub ${app}
            fi
          '') flatpakApps)}

          echo "Flatpak setup complete."
        '';

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
      };
    in
    {
      darwinConfigurations."macos_personal" = nix-darwin.lib.darwinSystem {
        modules = [
          brewPackagesModule_shared
          macosConfigModule_shared
          macosPackagesModule_shared
          macosConfigModule_personal
          nix-homebrew.darwinModules.nix-homebrew
          ./services/yabai.nix
          ./services/skhd.nix
        ];
      };
      darwinConfigurations."macos_work" = nix-darwin.lib.darwinSystem {
        modules = [
          brewPackagesModule_shared
          macosConfigModule_shared
          macosPackagesModule_shared
          macosConfigModule_work
          nix-homebrew.darwinModules.nix-homebrew
          ./services/yabai.nix
          ./services/skhd.nix
        ];
      };
      homeConfigurations."fedora_personal" = home-manager.lib.homeManagerConfiguration {
        pkgs = inputs.nixpkgs.legacyPackages."x86_64-linux";
        modules = [
          fedoraConfigModule
        ];
      };
      packages = {
        # macOS packages for aarch64-darwin
        aarch64-darwin = {
          personal = self.darwinConfigurations."macos_personal".config.system.build.toplevel;
          work = self.darwinConfigurations."macos_work".config.system.build.toplevel;
        };
        # Linux packages for x86_64-linux
        x86_64-linux = {
          personal = self.nixosConfigurations."fedora_personal".config.system.build.toplevel;
        };
      };
    };
}
