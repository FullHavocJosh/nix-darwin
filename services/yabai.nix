{ pkgs, ... }: {
  services.yabai = {
    enable = true;
    package = pkgs.yabai;
    enableScriptingAddition = true;
    config = {
      layout = "bsp";
      auto_balance = "off";

      mouse_modifier = "alt";
      mouse_action1 = "move";
      mouse_action2 = "resize";

      # gaps
      top_padding = 4;
      bottom_padding = 4;
      left_padding = 4;
      right_padding = 4;
      window_gap = 4;
    };
    extraConfig = ''
      yabai -m signal --add event=dock_did_restart action="sudo yabai --load-sa"

      # ===== Tiling setting =========================

      yabai -m config mouse_follows_focus         off
      yabai -m config focus_follows_mouse         off

      yabai -m config window_topmost              off
      yabai -m config window_opacity              off
      yabai -m config window_shadow               float

      yabai -m config window_border               on
      yabai -m config window_border_width         2
      yabai -m config active_window_border_color  "0xE0808080"
      yabai -m config normal_window_border_color  "0x00010101"
      yabai -m config insert_feedback_color       "0xE02d74da"

      yabai -m config active_window_opacity       1.0
      yabai -m config normal_window_opacity       0.90
      yabai -m config split_ratio                 0.50

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
