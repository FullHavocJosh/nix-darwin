return {
	{
		"neovim/nvim-lspconfig",
		dependencies = { "hrsh7th/cmp-nvim-lsp", "williamboman/mason-lspconfig.nvim", "glepnir/lspsaga.nvim" },
		config = function()
			local lspconfig = require("lspconfig")
			local capabilities = require("cmp_nvim_lsp").default_capabilities()
			local keymap = vim.keymap

			local signs = { Error = " ", Warn = " ", Hint = "ﴞ ", Info = " " }
			for type, icon in pairs(signs) do
				local hl = "DiagnosticSign" .. type
				vim.fn.sign_define(hl, { text = icon, texthl = hl, numhl = "" })
			end

			local augroup = vim.api.nvim_create_augroup("LspFormatting", {})

			local on_attach = function(client, bufnr)
				local opts = { noremap = true, silent = true, buffer = bufnr }
				keymap.set("n", "gf", "<cmd>Lspsaga lsp_finder<CR>", opts)
				keymap.set("n", "gD", "<Cmd>lua vim.lsp.buf.declaration()<CR>", opts)
				keymap.set("n", "gd", "<cmd>Lspsaga peek_definition<CR>", opts)
				keymap.set("n", "gi", "<cmd>lua vim.lsp.buf.implementation()<CR>", opts)
				keymap.set("n", "<leader>ca", "<cmd>Lspsaga code_action<CR>", opts)
				keymap.set("n", "<leader>rn", "<cmd>Lspsaga rename<CR>", opts)
				keymap.set("n", "<leader>D", "<cmd>Lspsaga show_line_diagnostics<CR>", opts)
				keymap.set("n", "<leader>d", "<cmd>Lspsaga show_cursor_diagnostics<CR>", opts)
				keymap.set("n", "[d", "<cmd>Lspsaga diagnostic_jump_prev<CR>", opts)
				keymap.set("n", "]d", "<cmd>Lspsaga diagnostic_jump_next<CR>", opts)
				keymap.set("n", "K", "<cmd>Lspsaga hover_doc<CR>", opts)
				keymap.set("n", "<leader>o", "<cmd>LSoutlineToggle<CR>", opts)

				if client.name == "tsserver" then
					keymap.set("n", "<leader>rf", ":TypescriptRenameFile<CR>", opts)
					keymap.set("n", "<leader>oi", ":TypescriptOrganizeImports<CR>", opts)
					keymap.set("n", "<leader>ru", ":TypescriptRemoveUnused<CR>", opts)
				end

				if client.name == "terraformls" then
					vim.api.nvim_create_autocmd("BufWritePre", {
						group = vim.api.nvim_create_augroup("TerraformFmt", { clear = true }),
						buffer = bufnr,
						callback = function()
							vim.lsp.buf.format({ bufnr = bufnr })
						end,
					})
				end

				if client.supports_method("textDocument/formatting") then
					vim.api.nvim_clear_autocmds({ group = augroup, buffer = bufnr })
					vim.api.nvim_create_autocmd("BufWritePre", {
						group = augroup,
						buffer = bufnr,
						callback = function()
							vim.lsp.buf.format({
								filter = function(fmt_client)
									return fmt_client.name == client.name
								end,
								bufnr = bufnr,
							})
						end,
					})
				end
			end

			local servers = {
				ansiblels = {},
				bashls = {},
				jsonls = {
					settings = {
						json = {
							schemas = {
								{
									fileMatch = { "package.json" },
									url = "https://json.schemastore.org/package.json",
								},
								{
									fileMatch = { "tsconfig*.json" },
									url = "https://json.schemastore.org/tsconfig.json",
								},
							},
						},
					},
				},
				lua_ls = {
					settings = {
						Lua = {
							format = { enable = true },
							diagnostics = {
								globals = { "vim" },
							},
						},
					},
				},
				rnix = {},
				powershell_es = {},
				tflint = {},
				yamlls = {
					settings = {
						yaml = {
							schemas = {
								kubernetes = "/*.k8s.yaml",
								["https://json.schemastore.org/ansible-playbook"] = "/ansible/*.{yaml,yml}",
							},
						},
					},
				},
				terraformls = {},
			}

			for server, config in pairs(servers) do
				lspconfig[server].setup(vim.tbl_deep_extend("force", {
					capabilities = capabilities,
					on_attach = on_attach,
				}, config))
			end
		end,
	},
}
