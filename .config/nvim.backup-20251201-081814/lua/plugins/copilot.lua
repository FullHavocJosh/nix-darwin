return {
	{
		"github/copilot.vim",
		event = "InsertEnter",
		config = function()
			vim.g.copilot_no_tab_map = true
			vim.g.copilot_assume_mapped = true
			vim.g.copilot_tab_fallback = ""

			vim.keymap.set("i", "<Tab>", 'copilot#Accept("")', {
				expr = true,
				replace_keycodes = false,
			})

			vim.keymap.set("i", "<C-;>", "copilot#Next()", {
				expr = true,
				replace_keycodes = false,
			})

			vim.keymap.set("i", "<C-,>", "copilot#Previous()", {
				expr = true,
				replace_keycodes = false,
			})
		end,
	},
	{
		"zbirenbaum/copilot-cmp",
		dependencies = {
			"github/copilot.vim",
			"hrsh7th/nvim-cmp",
		},
		event = "InsertEnter",
		config = function()
			require("copilot_cmp").setup()
		end,
	},
}
