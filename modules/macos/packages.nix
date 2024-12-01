{ pkgs, config, ... }:{

  ################################################
  ### Applications Shared Across MacOS Devices ###
  ################################################

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
}
