return {
	{
		"folke/which-key.nvim",
		event = "VeryLazy",
		init = function()
			vim.o.timeout = true
			vim.o.timeoutlen = 300
		end,
		config = function()
			local wk = require("which-key")
			wk.setup({
				plugins = {
					marks = true,
					registers = true,
					spelling = {
						enabled = true,
						suggestions = 20,
					},
				},
				win = {
					border = "rounded",
					position = "bottom",
					margin = { 1, 0, 1, 0 },
					padding = { 2, 2, 2, 2 },
				},
				layout = {
					height = { min = 4, max = 25 },
					width = { min = 20, max = 50 },
					spacing = 3,
					align = "left",
				},
			})

			-- Register key descriptions using new format
			wk.add({
				{ "<leader>+", desc = "Increment number" },
				{ "<leader>-", desc = "Decrement number" },
				{ "<leader>/", desc = "Toggle comments" },
				{ "<leader>b", desc = "List buffers" },
				{ "<leader>c", group = "Code" },
				{ "<leader>ca", desc = "Code actions" },
				{ "<leader>d", desc = "Show diagnostics" },
				{ "<leader>e", desc = "Toggle file explorer" },
				{ "<leader>f", desc = "Find files" },
				{ "<leader>g", group = "Git" },
				{ "<leader>gc", desc = "Git commits" },
				{ "<leader>gs", desc = "Git status" },
				{ "<leader>h", desc = "Help tags" },
				{ "<leader>r", group = "Rename/Refactor" },
				{ "<leader>rn", desc = "Rename symbol" },
				{ "<leader>x", desc = "Close buffer" },
				{ "<leader>1", desc = "Go to buffer 1" },
				{ "<leader>2", desc = "Go to buffer 2" },
				{ "<leader>3", desc = "Go to buffer 3" },
				{ "<leader>4", desc = "Go to buffer 4" },
				{ "<leader>5", desc = "Go to buffer 5" },
				{ "K", desc = "Show hover documentation" },
				{ "gd", desc = "Go to definition" },
				{ "<Tab>", desc = "Next buffer" },
				{ "<S-Tab>", desc = "Previous buffer" },
			})
		end,
	},
}