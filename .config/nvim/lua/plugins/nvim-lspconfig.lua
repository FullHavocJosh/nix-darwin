return {
	{
		"neovim/nvim-lspconfig",
		dependencies = { "hrsh7th/cmp-nvim-lsp", "williamboman/mason-lspconfig.nvim", "glepnir/lspsaga.nvim" },
		config = function()
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
				-- LSP keybindings are defined in keymaps.lua to avoid conflicts
				-- Only set TypeScript-specific keybindings here

				if client.name == "ts_ls" or client.name == "tsserver" then
					keymap.set("n", "<leader>rf", ":TypescriptRenameFile<CR>", opts)
					keymap.set("n", "<leader>oi", ":TypescriptOrganizeImports<CR>", opts)
					keymap.set("n", "<leader>ru", ":TypescriptRemoveUnused<CR>", opts)
				end

				-- Terraform formatting is handled by formatter-nvim using terraform fmt

				-- Only format terraform files via LSP, others use formatter-nvim
				-- if client.supports_method("textDocument/formatting") then
				--	vim.api.nvim_clear_autocmds({ group = augroup, buffer = bufnr })
				--	vim.api.nvim_create_autocmd("BufWritePre", {
				--		group = augroup,
				--		buffer = bufnr,
				--		callback = function()
				--			vim.lsp.buf.format({
				--				filter = function(fmt_client)
				--					return fmt_client.name == client.name
				--				end,
				--				bufnr = bufnr,
				--			})
				--		end,
				--	})
				-- end
			end

			local servers = {
				ansiblels = {},
				bashls = {},
				dockerls = {},
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
				pylsp = {
					settings = {
						pylsp = {
							plugins = {
								pycodestyle = { enabled = false },
								mccabe = { enabled = false },
								pyflakes = { enabled = false },
								flake8 = { enabled = true },
								autopep8 = { enabled = false },
								yapf = { enabled = false },
								black = { enabled = true },
							},
						},
					},
				},
				ts_ls = {},
				yamlls = {
					settings = {
						yaml = {
							schemas = {
								kubernetes = "/*.k8s.yaml",
								["https://json.schemastore.org/ansible-playbook"] = "/ansible/*.{yaml,yml}",
								["https://raw.githubusercontent.com/aws/aws-cloudformation-templates/main/aws-cfn-template-2010-09-09.json"] = "/*cloudformation*.{yaml,yml}",
							},
							validate = true,
							format = { enable = true },
						},
					},
				},
				terraformls = {},
			}

			for server, config in pairs(servers) do
				vim.lsp.config[server] = vim.tbl_deep_extend("force", {
					capabilities = capabilities,
					on_attach = on_attach,
				}, config)
			end
		end,
	},
}
