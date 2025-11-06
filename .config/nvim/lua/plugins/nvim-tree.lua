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
				highlight_opened_files = "none",
				highlight_modified = "name",
				icons = {
					show = {
						file = true,
						folder = true,
						folder_arrow = true,
						git = true,
						modified = true,
					},
					glyphs = {
						modified = "●",
					},
				},
			},
			filters = {
				dotfiles = false,
			},
			actions = {
				open_file = {
					quit_on_open = false,
				},
			},
			filesystem_watchers = {
				enable = true,
				debounce_delay = 50,
				ignore_dirs = {
					"node_modules",
					".git",
				},
			},
			modified = {
				enable = true,
				show_on_dirs = true,
				show_on_open_dirs = true,
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
