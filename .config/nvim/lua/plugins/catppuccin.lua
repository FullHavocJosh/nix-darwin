return {
	"catppuccin/nvim",
	name = "catppuccin",
	priority = 1000,
	lazy = false,
	transparent = true,
	config = function()
		-- Enable transparent background
		require("catppuccin").setup({
			style = "mocha", -- Optional: Choose your preferred color scheme style (e.g., 'frappe', 'mocha')
		})
		-- Load the theme
		require("catppuccin")
	end,
}
