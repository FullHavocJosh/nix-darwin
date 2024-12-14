{ pkgs, ... }: {
  services.skhd = {
    enable = true;
    skhdConfig = ''
      lctrl - h : yabai -m window --focus west
      lctrl - j : yabai -m window --focus south
      lctrl - k : yabai -m window --focus north
      lctrl - l : yabai -m window --focus east

      lctrl + shift - h : yabai -m display --focus west
      lctrl + shift - l : yabai -m display --focus east

      lctrl - e : yabai -m space --balance

      lctrl + shift - space : \
        yabai -m window --toggle float; \
        yabai -m window --toggle border

      lcrtl - f : yabai -m window --toggle zoom-fullscreen
    '';
  };
}
