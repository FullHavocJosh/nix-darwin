{ pkgs, config, ... }: {

  ################################################
  ### Applications Shared Across MacOS Devices ###
  ################################################

  environment.systemPackages = with pkgs; [ ];

  # brew tap FelixKratz/formulae

  homebrew = {
    enable = true;
    taps = [
      "warrensbox/tap"
      "nikitabobko/tap"
    ];
    # Install Brew Formulas
    brews = [
      "ansible"
      "ansible-lint"
      "atuin"
      "borders"
      "btop"
      "cmake"
      "eza"
      "fastfetch"
      "fzf"
      "go"
      "golangci-lint"
      "golangci-lint-langserver"
      "luarocks"
      "neovim"
      "mas"
      "oh-my-posh"
      "opentofu"
      "prettier"
      "python3"
      "speedtest-cli"
      "sshpass"
      "stow"
      "syncthing"
      "reattach-to-user-namespace"
      "rust"
      "telnet"
      "terraform-inventory"
      "terraform-ls"
      "terraform-lsp"
      "terraformer"
      "tflint"
      "tfswitch"
      "tldr"
      "tmux"
      "tpm"
      "watch"
      "zplug"
      "bash-language-server"
      "lua-language-server"
      "yaml-language-server"
    ];
    # Install Brew Casks
    casks = [
      "aerospace"
      "alacritty"
      "balenaetcher"
      "betterdisplay"
      "bettermouse"
      "brew install font-hack-nerd-font"
      "font-jetbrains-mono"
      "font-jetbrains-mono-nerd-font"
      "goland"
      "hyper"
      "jetbrains-toolbox"
      "krita"
      "lm-studio"
      "plexamp"
      "proton-pass"
      "qmk-toolbox"
      "raycast"
      "shottr"
      "stats"
      "sublime-text"
      "the-unarchiver"
      "vanilla"
      "via"
      "vlc"
      "zen-browser"
    ];
    # Install App Store Apps, search for ID with "mas search "
    # You must be logged into the Apps Store, and you must have purchased the app
    masApps = {
      "Xcode" = 497799835;
    };
    # This Setting will REMOVE apps that are installed by homebrew outside of this config
    onActivation.cleanup = "zap";
    # These Settings will perform "brew update" & "brew upgrade" when services-rebuild is run
    onActivation.autoUpdate = true;
    onActivation.upgrade = true;
  };
}
