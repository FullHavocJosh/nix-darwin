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
				adaptive_size = true,
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
					quit_on_open = false,
				},
			},
		})
		
		-- Auto-open NvimTree on startup
		vim.api.nvim_create_autocmd("VimEnter", {
			pattern = "*",
			callback = function()
				vim.defer_fn(function()
					vim.cmd("NvimTreeToggle")
				end, 100)
			end,
		})
	end,
}
