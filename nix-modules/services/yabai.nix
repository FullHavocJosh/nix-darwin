{ pkgs, ... }: {
  services.yabai = {
    enable = true;
    package = pkgs.yabai;
    enableScriptingAddition = true;
    config = {
      layout = "bsp";
      auto_balance = "off";
      top_padding = 5;
      bottom_padding = 5;
      left_padding = 5;
      right_padding = 5;
      window_gap = 5;
      insert_feedback_color = "0xFFFFFFFF";
      window_topmost = "on";
      window_opacity = "on";
      window_shadow = "float";
      active_window_opacity = 1.0;
      normal_window_opacity = 0.9;
      split_ratio = 0.5;
      mouse_modifier = "alt";
      mouse_action1 = "move";
      focus_follows_mouse = "off";
      mouse_follows_focus = "off";
    };
    extraConfig = ''
      yabai -m signal --add event=dock_did_restart action="sudo yabai --load-sa"

      # ===== Rules ==================================

      yabai -m rule --add app="^Finder$" title="(Co(py|nnect)|Move|Info|Pref)" manage=off
      yabai -m rule --add app="^Safari$" title="^(General|(Tab|Password|Website|Extension)s|AutoFill|Se(arch|curity)|Privacy|Advance)$" manage=off
      yabai -m rule --add app="^System Settings$" manage=off
      yabai -m rule --add app="^App Store$" manage=off
      yabai -m rule --add app="^Activity Monitor$" manage=off
      yabai -m rule --add app="^Calculator$" manage=off
      yabai -m rule --add app="^Dictionary$" manage=off
      yabai -m rule --add label="Software Update" title="Software Update" manage=off
      yabai -m rule --add app="System Information" manage=off
      yabai -m rule --add app="Passwords" manage=off
      yabai -m rule --add app="^Vanilla$" title="^Preferences$" manage=off
      yabai -m rule --add app="^Cisco AnyConnect Secure Mobility Client$" manage=off
      yabai -m rule --add app="^Shottr$" manage=off
      yabai -m rule --add app="GoLand" title="Settings" manage=off
    '';
  };
}
