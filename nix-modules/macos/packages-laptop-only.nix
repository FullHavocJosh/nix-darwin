{ pkgs, ... }:
{
  homebrew = {
    enable = true;
    casks = [
      "plexamp"
      "proton-pass"
    ];
  };
}
