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

      ############################################
      ### MacOS Settings Shared Across Devices ###
      ############################################

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
      # List packages installed in system profile. To search by name, run:
      # $ nix-env -qaP | grep wget
      # or search.nixos.org
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
          # Install App Store Apps, search for ID with "mas search "
          # You must be logged into the Apps Store, and you must have purchased the app
          masApps = {
            "Noir for Safari" = 1592917505;
            "Xcode" = 497799835;
          };
          # This Setting will REMOVE apps that are installed by homebrew outside of this config
          onActivation.cleanup = "zap";
          # These Settings will perform "brew update" & "brew upgrade" when services-rebuild is run
          onActivation.autoUpdate = true;
          onActivation.upgrade = true;
        };
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
      };
      macosPackagesModule_personal = { pkgs, config, ... }: {
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
      };
      macosPackagesModule_work = { pkgs, config, ... }: {
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

      ############################################
      ### Fedora Settings for Personal Devices ###
      ############################################

      fedoraConfigModule = { pkgs, config, ... }: {
        system.stateVersion = "23.05"; # Set to your NixOS stable release version
        nixpkgs.config = {
          allowUnfree = true; # Globally allow unfree packages
          allowUnfreePredicate = pkg:
            builtins.elem (pkgs.lib.getName pkg) [ "terraform" "terraform-ls" ];
        };
        fileSystems."/" = {
          device = "/dev/disk/by-uuid/9a09856b-679d-4e98-89d8-90ca8892a3da";
          fsType = "ext4";
        };
        boot.loader = {
          systemd-boot.enable = false;
          grub.enable = false;
        };
        environment.systemPackages = with pkgs; [
          atuin
          btop
          eza
          fzf
          python3
          stow
          tmux
          zplug
          neovim
          terraform
          lua-language-server
          vlc
        ];
        system.activationScripts.stow.text = ''
          echo "Stowing dotfiles for Fedora..."
          /run/current-system/sw/bin/stow -t /home/havoc -d /home/havoc/nix-darwin
          echo "Stow applied successfully."
        '';
      };
    in
    {
      darwinConfigurations."macos_personal" = nix-darwin.lib.darwinSystem {
        modules = [
          macosConfigModule_shared
          macosPackagesModule_shared
          macosPackagesModule_personal
          macosConfigModule_personal
          nix-homebrew.darwinModules.nix-homebrew
          ./services/yabai.nix
          ./services/skhd.nix
        ];
      };
      darwinConfigurations."macos_work" = nix-darwin.lib.darwinSystem {
        modules = [
          macosConfigModule_shared
          macosPackagesModule_shared
          macosPackagesModule_work
          macosConfigModule_work
          nix-homebrew.darwinModules.nix-homebrew
          ./services/yabai.nix
          ./services/skhd.nix
        ];
      };
      nixosConfigurations."fedora_personal" = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
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
