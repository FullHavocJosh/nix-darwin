return {
	{
		"folke/which-key.nvim",
		event = "VeryLazy",
		init = function()
			vim.o.timeout = true
			vim.o.timeoutlen = 500
		end,
		config = function()
			local wk = require("which-key")
			wk.setup({
				preset = "modern",
				delay = 300,
				win = {
					no_overlap = true,
					padding = { 1, 2 },
					title = true,
					title_pos = "center",
					zindex = 1000,
				},
				layout = {
					width = { min = 20, max = 50 },
					spacing = 3,
					align = "left",
				},
				plugins = {
					marks = true,
					registers = true,
					spelling = {
						enabled = true,
						suggestions = 20,
					},
				},
			})

			-- Register key descriptions using new format
			wk.add({
				{ "<leader>b", desc = "List buffers" },
				{ "<leader>c", group = "Code" },
				{ "<leader>ca", desc = "Code actions" },
				{ "<leader>d", desc = "Show diagnostics" },
				{ "<leader>e", desc = "Toggle file explorer" },
				{ "<leader>f", desc = "Find files" },
				{ "<leader>fs", desc = "Fix syntax highlighting" },
				{ "<leader>g", group = "Git" },
				{ "<leader>gc", desc = "Git commits" },
				{ "<leader>gs", desc = "Git status" },
				{ "<leader>h", desc = "Help tags" },
				{ "<leader>r", group = "Rename/Refactor" },
				{ "<leader>rn", desc = "Rename symbol" },
				{ "<leader>rf", desc = "Rename file (TS)" },
				{ "<leader>oi", desc = "Organize imports (TS)" },
				{ "<leader>ru", desc = "Remove unused (TS)" },
				{ "<leader>s", group = "Search/Replace" },
				{ "<leader>sw", desc = "Search word" },
				{ "<leader>sp", desc = "Search in file" },
				{ "<leader>w", group = "Window" },
				{ "<leader>wv", desc = "Split vertical" },
				{ "<leader>wh", desc = "Split horizontal" },
				{ "<leader>w=", desc = "Equal splits" },
				{ "<leader>wc", desc = "Close window" },
				{ "<leader>w+", desc = "Increase height" },
				{ "<leader>w-", desc = "Decrease height" },
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