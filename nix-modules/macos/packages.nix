{ pkgs, config, ... }:
{
  environment.systemPackages = with pkgs; [
    nil
    smassh
    python3Packages.fonttools # For creating font aliases
    lemminx # XML Language Server
    rubyPackages.rubocop # Ruby linter/formatter
  ];

  homebrew = {
    enable = true;
    taps = [
      "warrensbox/tap"
      "nikitabobko/tap"
      "charmbracelet/tap"
    ];
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
      "djlint"
      "dockerfile-language-server"
      "exiftool"
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
      "lazygit"
      "lua-language-server"
      "luarocks"
      "mas"
      "neovide"
      "neovim"
      "nixfmt"
      "opencode"
      "opentofu"
      "prettier"
      "python-lsp-server"
      "python3"
      "reattach-to-user-namespace"
      "ripgrep"
      "ruff"
      "rust"
      "rust-analyzer"
      "shfmt"
      "solargraph"
      "speedtest-cli"
      "sshpass"
      "starship"
      "stow"
      "stylua"
      "superfile"
      "syncthing"
      "taplo"
      "tealdeer"
      "telnet"
      "terraform-inventory"
      "terraform-ls"
      "terraform-lsp"
      "terraformer"
      "tflint"
      "tfswitch"
      "tmux"
      "tpm"
      "tree-sitter"
      "typescript-language-server"
      "uv"
      "vscode-langservers-extracted"
      "watch"
      "yaml-language-server"
      "yamllint"
      "zoxide"
      "zplug"
      "ansible-language-server"
    ];
    casks = [
      "aerospace"
      "alacritty"
      "balenaetcher"
      "betterdisplay"
      "claude"
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
      "neovide-app"
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
    masApps = {
      "Xcode" = 497799835;
    };
    onActivation.cleanup = "zap";
    onActivation.autoUpdate = true;
    onActivation.upgrade = true;
  };
}
