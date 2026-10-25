{ pkgs, ... }:
{
  homebrew = {
    enable = true;
    casks = [
      "plexamp"
      "proton-pass"
      "steam"
      "utm" # Linux VMs (arm64 native, x86_64 via QEMU/Rosetta) and macOS guests
    ];
  };
}
