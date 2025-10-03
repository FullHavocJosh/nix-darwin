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
      "charmbracelet/tap"
    ];
    # Install Brew Formulas
    brews = [
      "ansible"
      "ansible-lint"
      "atuin"
      "awscli"
      "bash-language-server"
      "borders"
      "btop"
      "cmake"
      "coreutils"
      "crush"
      "dockerfile-language-server"
      "eza"
      "fastfetch"
      "fd"
      "fzf"
      "gh"
      "go"
      "golangci-lint"
      "golangci-lint-langserver"
      "gopls"
      "graphviz"
      "hadolint"
      "jq"
      "lua-language-server"
      "luarocks"
      "mas"
      "neovim"
      "nixfmt"
      "oh-my-posh"
      "opentofu"
      "prettier"
      "python-lsp-server"
      "python3"
      "reattach-to-user-namespace"
      "ripgrep"
      "rust"
      "speedtest-cli"
      "sshpass"
      "starship"
      "stow"
      "switchaudio-osx"
      "syncthing"
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
      "typescript-language-server"
      "uv"
      "watch"
      "yaml-language-server"
      "yamllint"
      "zoxide"
      "zplug"
      "ansible-language-server"
    ];
    # Install Brew Casks
    casks = [
      "aerospace"
      "alacritty"
      "balenaetcher"
      "betterdisplay"
      "claude"
      "claude-code"
      "font-hack-nerd-font"
      "font-jetbrains-mono-nerd-font"
      "ghostty"
      "goland"
      "hyper"
      "jetbrains-toolbox"
      "kitty"
      "krita"
      "librewolf"
      "lm-studio"
      "plexamp"
      "proton-pass"
      "qmk-toolbox"
      "raycast"
      "sf-symbols"
      "shottr"
      "stats"
      "sublime-text"
      "ungoogled-chromium"
      "vanilla"
      "via"
      "vial"
      "vlc"
      "zen"
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
