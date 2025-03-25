return {
	"catppuccin/nvim",
	name = "catppuccin",
	priority = 1000,
	lazy = false,
	transparent = true,
	config = function()
		require("catppuccin").setup({
			style = "mocha",
			dim_inactive = {
				enabled = true,
			},
			transparent_backgroundansparent_backgrond = true,
			cmp = true,
			telescope = true,
			nvimtree = {
				enabled = true,
				transparent_panel = true,
			},
			bufferline = {
				enabled = true,
			},
		})
		require("catppuccin")
	end,
}
