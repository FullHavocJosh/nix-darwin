-- Neovide-specific configuration
-- Only applies when running Neovim through Neovide

if vim.g.neovide then
	-- Font configuration (matching Ghostty: JetBrains Mono, size 14)
	vim.o.guifont = "JetBrainsMono_Nerd_Font:h14"

	-- Window padding (matching Ghostty: 0 padding)
	vim.g.neovide_padding_top = 0
	vim.g.neovide_padding_bottom = 0
	vim.g.neovide_padding_left = 0
	vim.g.neovide_padding_right = 0

	-- Window blur (matching Ghostty: background-blur = true)
	vim.g.neovide_window_blurred = true

	-- Refresh rate
	vim.g.neovide_refresh_rate = 60

	-- Additional quality settings
	vim.g.neovide_refresh_rate_idle = 5

	-- Floating window blur
	vim.g.neovide_floating_blur_amount_x = 2.0
	vim.g.neovide_floating_blur_amount_y = 2.0

	-- Floating window shadow
	vim.g.neovide_floating_shadow = true
	vim.g.neovide_floating_z_height = 10
	vim.g.neovide_light_angle_degrees = 45
	vim.g.neovide_light_radius = 5

	-- Cursor settings
	vim.g.neovide_cursor_animation_length = 0.05
	vim.g.neovide_cursor_trail_size = 0.3
	vim.g.neovide_cursor_antialiasing = true
	vim.g.neovide_cursor_animate_in_insert_mode = true
	vim.g.neovide_cursor_animate_command_line = true
	vim.g.neovide_cursor_unfocused_outline_width = 0.125

	-- No cursor particles (keeping it simple like Ghostty)
	vim.g.neovide_cursor_vfx_mode = ""

	-- Scale factor
	vim.g.neovide_scale_factor = 1.0

	-- Remember window size
	vim.g.neovide_remember_window_size = true

	-- Confirm quit
	vim.g.neovide_confirm_quit = false

	-- macOS-specific settings (matching Ghostty behavior)
	if vim.fn.has("mac") == 1 then
		vim.g.neovide_input_macos_option_key_is_meta = "only_left"
	end
end
