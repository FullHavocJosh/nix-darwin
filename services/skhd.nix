{ pkgs, ... }: {
  services.skhd = {
    enable = true;
    skhdConfig = ''
      # ############################################################### #
      # THE FOLLOWING CONFIGURATION IS TAKEN FROM:                      #
      # https://github.com/julian-heng/yabai-config/blob/master/skhdrc  #
      # ############################################################### #

      # opens Alacritty
      #lctrl - return : $HOME/.config/yabai/.scripts/open_alacritty.sh

      # Focus windows in the specified direction
      lctrl - h : yabai -m window --focus west
      lctrl - j : yabai -m window --focus south
      lctrl - k : yabai -m window --focus north
      lctrl - l : yabai -m window --focus east

      # Move focus to monitors in the specified direction
      lctrl - alt - h : yabai -m display --focus west
      lctrl - alt - l : yabai -m display --focus east

      # Moving windows
      #lctrl + shift - h : yabai -m window --warp west
      #lctrl + shift - j : yabai -m window --warp south
      #lctrl + shift - k : yabai -m window --warp north
      #lctrl + shift - l : yabai -m window --warp east

      # Resize windows
      #lctrl + alt - h : yabai -m window --resize left:-50:0; \
      #                  yabai -m window --resize right:-50:0
      #lctrl + alt - j : yabai -m window --resize bottom:0:50; \
      #                  yabai -m window --resize top:0:50
      #lctrl + alt - k : yabai -m window --resize top:0:-50; \
      #                  yabai -m window --resize bottom:0:-50
      #lctrl + alt - l : yabai -m window --resize right:50:0; \
      #                  yabai -m window --resize left:50:0

      # Equalize size of windows
      lctrl + alt - e : yabai -m space --balance

      # Enable / Disable gaps in current workspace
      #lctrl + alt - g : yabai -m space --toggle padding; yabai -m space --toggle gap

      # Rotate windows clockwise and anticlockwise
      #alt - r         : yabai -m space --rotate 270
      #shift + alt - r : yabai -m space --rotate 90

      # Rotate on X and Y Axis
      #shift + alt - x : yabai -m space --mirror x-axis
      #shift + alt - y : yabai -m space --mirror y-axis

      # Set insertion point for focused container
      #shift + lctrl + alt - h : yabai -m window --insert west
      #shift + lctrl + alt - j : yabai -m window --insert south
      #shift + lctrl + alt - k : yabai -m window --insert north
      #shift + lctrl + alt - l : yabai -m window --insert east

      # Float / Unfloat window
      lctrl + shift - space : \
          yabai -m window --toggle float; \
          yabai -m window --toggle border

      # Make window fullscreen
      lctrl - f         : yabai -m window --toggle zoom-fullscreen
    '';
  };
}
