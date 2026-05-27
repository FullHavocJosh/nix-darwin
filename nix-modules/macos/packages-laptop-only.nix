# GUI applications for laptop ONLY
# Not shared with work or desktop
{ pkgs, ... }:
{
  homebrew = {
    enable = true;
    casks = [
      # Laptop-specific utilities
      "plexamp"
      "proton-pass"
    ];
  };
}
