return {
	"nvim-tree/nvim-tree.lua",
	version = "*",
	lazy = false,
	transparent = true,
	dependencies = {
		"nvim-tree/nvim-web-devicons",
	},
	config = function()
		require("nvim-tree").setup({
			view = {
				side = "left",
				width = 30,
				preserve_window_proportions = true,
			},
		})
	end,
}
