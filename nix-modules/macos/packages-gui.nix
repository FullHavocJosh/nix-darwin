# GUI applications for laptop and work
# Desktop is SSH-only (TUI tools from packages-tui.nix)
# TUI/CLI apps shared across all profiles are in packages-tui.nix
{ pkgs, ... }:
{
  homebrew = {
    enable = true;
    casks = [
      # Window Management
      "nikitabobko/tap/aerospace"

      # Terminals
      "alacritty"
      "ghostty"
      "hyper"
      "kitty"

      # AI Tools
      "claude"
      "claude-code"
      "lm-studio"

      # Development IDEs
      "goland"
      "jetbrains-toolbox"
      "sublime-text"
      "zed"

      # Browsers
      "ungoogled-chromium"
      "zen"

      # Graphics & Media
      "krita"
      "vlc"

      # Utilities
      "balenaetcher"
      "betterdisplay"
      "xykong/tap/flux-markdown"
      "insta360-link-controller"
      "keepingyouawake"
      "neovide-app"
      "plexamp"
      "proton-pass"
      "qmk-toolbox"
      "sf-symbols"
      "shottr"
      "vanilla"
      "via"
      "vial"
    ];
  };
}
