{ pkgs, ... }:
{
  homebrew = {
    enable = true;
    taps = [ "SableClient/sable" ];
    casks = [
      "battle-net"
      "game-porting-toolkit"
      "krita"
      "moonlight"
      "proton-pass"
      "SableClient/sable/sable"
      "steam"
      "wowup-cf"
    ];
  };
}
