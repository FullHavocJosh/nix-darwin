{ pkgs, ... }: {
  services.skhd = {
    enable = true;
    skhdConfig = ''
      # Focus windows in the specified direction
      lctrl - h : yabai -m window --focus west
      lctrl - j : yabai -m window --focus south
      lctrl - k : yabai -m window --focus north
      lctrl - l : yabai -m window --focus east

      # Move focus to monitors in the specified direction
      lctrl + shift - h : yabai -m display --focus west
      lctrl + shift - l : yabai -m display --focus east

      # Equalize size of windows
      lctrl - e : yabai -m space --balance

      # Float / Unfloat window
      lctrl + shift - space : \
          yabai -m window --toggle float; \
          yabai -m window --toggle border

      # Make window fullscreen
      lctrl - f : yabai -m window --toggle zoom-fullscreen
    '';
  };
}
