{ pkgs, ... }:
{
  homebrew = {
    enable = true;
    taps = [ "SableClient/sable" ];
    casks = [
      "plexamp"
      "proton-pass"
      "SableClient/sable/sable"
      "steam"
    ];
  };
}
