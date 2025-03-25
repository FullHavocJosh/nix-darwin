return {
	{
		"akinsho/bufferline.nvim",
		version = "*",
		dependencies = { "nvim-tree/nvim-web-devicons", "catppuccin/nvim" },
		transparent = true,
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
			})
		end,
	},
}
