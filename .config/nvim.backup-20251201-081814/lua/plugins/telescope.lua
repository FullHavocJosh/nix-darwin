return {
	"nvim-telescope/telescope.nvim",
	tag = "0.1.8",
	dependencies = { 
		"nvim-lua/plenary.nvim",
		"nvim-telescope/telescope-fzf-native.nvim"
	},
	config = function()
		require("telescope").setup({
			defaults = {},
			pickers = {},
			extensions = {
				fzf = {
					fuzzy = false, -- false will only do exact matching
					override_generic_sorter = true, -- override the generic sorter
					override_file_sorter = true, -- override the file sorter
					case_mode = "smart_case", -- or "ignore_case" or "respect_case"
				},
			},
		})
		-- Load fzf extension
		require("telescope").load_extension("fzf")
	end,
}
