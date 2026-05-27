# GUI applications for laptop only
# Desktop is SSH-only (TUI tools from packages-tui.nix)
# Work has its own enterprise GUI apps in work.nix
{ pkgs, ... }:
{
  # GUI applications for laptop only (desktop is SSH-only with TUI tools)
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
      "warrensbox/tap/tfswitch"
      "vanilla"
      "via"
      "vial"
    ];
  };
}
