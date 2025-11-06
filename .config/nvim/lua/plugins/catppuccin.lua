return {
	"catppuccin/nvim",
	name = "catppuccin",
	priority = 1000,
	lazy = false,
	config = function()
		require("catppuccin").setup({
			style = "mocha",
			integrations = {
				telescope = true,
				nvimtree = {
					enabled = true,
				},
				bufferline = true,
				which_key = true,
				lsp_saga = true,
				treesitter = true,
				cmp = true,
				gitsigns = true,
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
