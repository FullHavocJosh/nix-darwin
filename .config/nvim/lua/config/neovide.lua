-- Neovide GUI-specific settings
if vim.g.neovide then
  vim.o.guifont = "JetBrainsMono_Nerd_Font:h14"

  vim.g.neovide_padding_top = 0
  vim.g.neovide_padding_bottom = 0
  vim.g.neovide_padding_left = 0
  vim.g.neovide_padding_right = 0

  vim.g.neovide_transparency = 0.8
  vim.g.neovide_window_blurred = true

  vim.g.neovide_refresh_rate = 60
  vim.g.neovide_refresh_rate_idle = 5

  vim.g.neovide_floating_blur_amount_x = 2.0
  vim.g.neovide_floating_blur_amount_y = 2.0

  vim.g.neovide_floating_shadow = true
  vim.g.neovide_floating_z_height = 10
  vim.g.neovide_light_angle_degrees = 45
  vim.g.neovide_light_radius = 5

  vim.g.neovide_cursor_animation_length = 0.05
  vim.g.neovide_cursor_trail_size = 0.3
  vim.g.neovide_cursor_antialiasing = true
  vim.g.neovide_cursor_animate_in_insert_mode = true
  vim.g.neovide_cursor_animate_command_line = true
  vim.g.neovide_cursor_unfocused_outline_width = 0.125
  vim.g.neovide_cursor_vfx_mode = ""

  vim.g.neovide_scale_factor = 1.0
  vim.g.neovide_remember_window_size = true
  vim.g.neovide_confirm_quit = false

  if vim.fn.has("mac") == 1 then
    vim.g.neovide_input_macos_option_key_is_meta = "only_left"
  end
end
