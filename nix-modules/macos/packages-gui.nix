# GUI applications for laptop and work
# Desktop is SSH-only (TUI tools from packages-tui.nix)
# TUI/CLI apps shared across all profiles are in packages-tui.nix
#
# PACKAGE POLICY: Prefer Homebrew for all new packages (brews/casks below).
# Only use environment.systemPackages for packages not available on Homebrew.
{ pkgs, ... }:
{
  homebrew = {
    enable = true;
    casks = [
      # Window Management
      "nikitabobko/tap/aerospace"

      # Terminals
      "ghostty"
      "hyper"
      "kitty"

      # AI Tools
      "claude"
      "claude-code"

      # Development IDEs
      "goland"
      "jetbrains-toolbox"

      # Browsers
      "ungoogled-chromium"
      "zen"

      # Graphics & Media
      "vlc"

      # Utilities
      "balenaetcher"
      "xykong/tap/flux-markdown"
      "insta360-link-controller"
      "keepingyouawake"
      "neovide-app"
      "sf-symbols"
      "shottr"
    ];
  };
}
