return {
	"catppuccin/nvim",
	name = "catppuccin",
	priority = 1000,
	lazy = false,
	transparent = true,
	config = function()
		require("catppuccin").setup({
			style = "mocha",
		})
		require("catppuccin")
	end,
}
