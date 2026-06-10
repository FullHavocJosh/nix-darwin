{ pkgs, ... }:
{
  networking.hostName = "MacMiniM1";
  networking.computerName = "MacMiniM1";

  homebrew.casks = [
    "ollama-app"
  ];
}
