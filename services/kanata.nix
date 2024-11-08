{ pkgs, ... }: {
  services.kanata  = {
  enable = true;
    description = "Kanata Input Remapper";
    startAt = "loginwindow";
    script = ''
      exec /opt/homebrew/bin/kanata --config ${config.home.homeDirectory}/.config/kanata/config.kdb
    '';
    serviceConfig = {
      KeepAlive = true;
      RunAtLoad = true;
      StandardErrorPath = "/var/log/kanata.log";
      StandardOutPath = "/var/log/kanata.log";
    };
  };
}