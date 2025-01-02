return {
	{
		"akinsho/bufferline.nvim",
		version = "*",
		dependencies = { "nvim-tree/nvim-web-devicons", "catppuccin/nvim" },
		config = function()
			local catppuccin = require("catppuccin.palettes").get_palette("mocha") -- Replace "mocha" with your preferred flavor
			local catppuccin_highlights = require("catppuccin.groups.integrations.bufferline").get()

			-- Ensure `catppuccin_highlights` is evaluated as a table
			if type(catppuccin_highlights) == "function" then
				catppuccin_highlights = catppuccin_highlights()
			end

			require("bufferline").setup({
				options = {
					numbers = "ordinal",
					close_command = "bdelete! %d",
					right_mouse_command = "bdelete! %d",
					left_mouse_command = "buffer %d",
					middle_mouse_command = nil,
					diagnostics = "nvim_lsp",
					offsets = {
						{
							filetype = "NvimTree",
							text = "File Explorer",
							text_align = "center",
						},
					},
					separator_style = "none", -- Remove separator bars entirely
					always_show_bufferline = true,
				},
				highlights = vim.tbl_extend("force", catppuccin_highlights, {
					-- Remove separator bars
					separator = {
						fg = catppuccin.mantle, -- Matches the background
						bg = catppuccin.mantle, -- Matches the tab background
					},
					separator_selected = {
						fg = catppuccin.mantle, -- Matches active tab background
						bg = catppuccin.mantle, -- Matches active tab background
					},
					separator_visible = {
						fg = catppuccin.mantle, -- Matches the background
						bg = catppuccin.mantle, -- Matches inactive tab background
					},

					-- Ensure inactive buffers are styled correctly
					background = {
						fg = catppuccin.overlay1, -- Dimmed text for inactive buffers
						bg = catppuccin.mantle, -- Match the inactive tab background
					},
					fill = {
						fg = catppuccin.overlay0, -- Dimmed text for unused area
						bg = catppuccin.mantle, -- Match the bar background
					},

					-- Indicator for active buffer (optional highlight tweak)
					indicator_selected = {
						fg = catppuccin.text, -- Optional: matches active buffer text
						bg = catppuccin.mantle, -- Matches active buffer background
					},
				}),
			})
		end,
	},
}
