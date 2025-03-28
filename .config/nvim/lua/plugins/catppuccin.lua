return {
	"catppuccin/nvim",
	name = "catppuccin",
	priority = 1000,
	lazy = false,
	transparent = true,
	config = function()
		require("catppuccin").setup({
			style = "mocha",
			transparent_backgroundansparent_backgrond = true,
			telescope = true,
			nvimtree = {
				enabled = true,
				transparent_panel = true,
			},
			overrides = function(catppuccin)
				return {
					nCursor = { bg = catppuccin.blue },
					vCursor = { bg = catppuccin.green },
					iCursor = { bg = catppuccin.red },
				}
			end,

		})
		require("catppuccin")
	end,
}
