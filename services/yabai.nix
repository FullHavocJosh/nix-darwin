{ pkgs, ... }: {
  services.yabai = {
    enable = true;
    package = pkgs.yabai;
    enableScriptingAddition = true;
    config = {
      layout = "bsp";
      auto_balance = "off";

      mouse_modifier = "alt";
      # set modifier + right-click drag to resize window (default: resize)
      mouse_action2 = "resize";
      # set modifier + left-click drag to resize window (default: move)
      mouse_action1 = "move";

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

      yabai -m config layout                      bsp

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

      yabai -m config auto_balance                off

      yabai -m config mouse_modifier              fn
      yabai -m config mouse_action1               move
      yabai -m config mouse_action2               resize

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
      yabai -m rule --add app="Cisco AnyConnect Secure Mobility Client" manage=off
      yabai -m rule --add app="Passwords" manage=off
      yabai -m rule --add label="Vanilla" manage=off
    '';
  };
}
