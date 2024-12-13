{ config, pkgs, ... }:
{
system.activationScripts.restartSkhd = ''
    #!/usr/bin/env bash
    echo "Restarting skhd..."
    pkill skhd || true
    echo "Restarted skhd..."
  '';
}
