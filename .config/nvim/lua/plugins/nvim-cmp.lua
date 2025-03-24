return {
	{
		"hrsh7th/nvim-cmp", -- Main completion plugin
		dependencies = {
			"hrsh7th/cmp-buffer", -- Source for text in buffer
			"hrsh7th/cmp-path", -- Source for file system paths
			"hrsh7th/cmp-nvim-lsp", -- LSP source for autocompletion
			"hrsh7th/cmp-vsnip", -- VSnip integration
			"L3MON4D3/LuaSnip", -- Snippet engine
			"saadparwaiz1/cmp_luasnip", -- LuaSnip source for nvim-cmp
			"rafamadriz/friendly-snippets", -- Predefined snippets
			"onsails/lspkind.nvim", -- VS Code-like pictograms
		},
		config = function()
			-- Import plugins safely
			local cmp = require("cmp")
			local luasnip = require("luasnip")
			local lspkind = require("lspkind")

			-- Load VS Code-like snippets
			require("luasnip.loaders.from_vscode").lazy_load()

			-- Set completeopt for better completion experience
			vim.opt.completeopt = "menu,menuone,noselect"

			-- Configure nvim-cmp
			cmp.setup({
				snippet = {
					expand = function(args)
						luasnip.lsp_expand(args.body) -- Use LuaSnip as the snippet engine
					end,
				},
				mapping = {
					["<C-k>"] = cmp.mapping.select_prev_item(),
					["<C-j>"] = cmp.mapping.select_next_item(),
					["<C-b>"] = cmp.mapping.scroll_docs(-4),
					["<C-f>"] = cmp.mapping.scroll_docs(4),
					["<C-Space>"] = cmp.mapping.complete(),
					["<C-e>"] = cmp.mapping.abort(),
					["<CR>"] = cmp.mapping.confirm({ select = true }),
				},
				sources = cmp.config.sources({
					{ name = "nvim_lsp" }, -- LSP completion
					{ name = "luasnip" }, -- Snippets completion
					{ name = "buffer" }, -- Text in buffer
					{ name = "path" }, -- File system paths
				}),
				-- Configure lspkind for VS Code-like pictograms
				formatting = {
					format = lspkind.cmp_format({
						maxwidth = 50, -- Limit completion item width
						ellipsis_char = "...", -- Ellipsis for long completion items
					}),
				},
				-- Don't automatically trigger completion
				completion = {
					autocomplete = false, -- Disable auto-triggering of the completion window
				},
			})
		end,
	},
}
