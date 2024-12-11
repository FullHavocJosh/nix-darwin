{ pkgs, config, ... }: {

  ################################################
  ### Applications Shared Across MacOS Devices ###
  ################################################

  environment.systemPackages = with pkgs; [
    atuin
    btop
    eza
    fzf
    mkalias
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
      "golangci-lint"
      "golangci-lint-langserver"
      "luarocks"
      "neovim"
      "mas"
      "oh-my-posh"
      "opentofu"
      "prettier"
      "starship"
      "syncthing"
      "reattach-to-user-namespace"
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
      "goland"
      "hyper"
      "iterm2"
      "jetbrains-toolbox"
      "kitty"
      "krita"
      "plexamp"
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
      "Xcode" = 497799835;
    };
    # This Setting will REMOVE apps that are installed by homebrew outside of this config
    onActivation.cleanup = "zap";
    # These Settings will perform "brew update" & "brew upgrade" when services-rebuild is run
    onActivation.autoUpdate = true;
    onActivation.upgrade = true;
  };
}
