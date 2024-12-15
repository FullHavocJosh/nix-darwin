{ pkgs, ... }: {
  services.skhd = {
    enable = true;
    skhdConfig = ''
      ctrl - h : yabai -m window --focus west
      ctrl - j : yabai -m window --focus south
      ctrl - k : yabai -m window --focus north
      ctrl - l : yabai -m window --focus east

      ctrl + shift - h : yabai -m display --focus west
      ctrl + shift - l : yabai -m display --focus east

      ctrl - e : yabai -m space --balance

      ctrl + shift - space : \
        yabai -m window --toggle float; \
        yabai -m window --toggle border
    '';
  };
}
