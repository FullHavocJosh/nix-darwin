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
			git = {
				enable = true,
			},
			view = {
				side = "left",
				width = 30,
			},
			sort = {
				sorter = "case_sensitive",
			},
			renderer = {
				group_empty = true,
			},
			filters = {
				dotfiles = false,
			},
			actions = {
				open_file = {
					quit_on_open = true,
				},
			},
		})
	end,
}
