return {
	"mhartington/formatter.nvim",
	config = function()
		require("formatter").setup({
			logging = false,
			filetype = {
				bash = {
					function()
						return {
							exe = "shfmt",
							args = { "-i", "2" },
							stdin = true,
						}
					end,
				},
				yaml = {
					function()
						return {
							exe = "prettier",
							args = { "--stdin-filepath", vim.fn.expand("%:p") },
							stdin = true,
						}
					end,
				},
				json = {
					function()
						return {
							exe = "prettier",
							args = { "--stdin-filepath", vim.fn.expand("%:p") },
							stdin = true,
						}
					end,
				},
				lua = {
					function()
						return {
							exe = "stylua",
							args = { "-" },
							stdin = true,
						}
					end,
				},
				python = {
					function()
						return {
							exe = "black",
							args = { "-" },
							stdin = true,
						}
					end,
				},
				terraform = {
					function()
						return {
							exe = "terraform",
							args = { "fmt", "-" },
							stdin = true,
						}
					end,
				},
				ps1 = {
					function()
						return {
							exe = "pwsh",
							args = {
								"-Command",
								'Invoke-Formatter -ScriptDefinition "$(cat ' .. vim.fn.expand("%:p") .. ')"',
							},
							stdin = false,
						}
					end,
				},

				ruby = {
					function()
						return {
							exe = "rubocop",
							args = { "-a", vim.fn.expand("%:p") },
							stdin = false,
						}
					end,
				},
				xml = {
					function()
						return {
							exe = "xmllint",
							args = { "--format", "-" },
							stdin = true,
						}
					end,
				},
				toml = {
					function()
						return {
							exe = "taplo",
							args = { "format", "-" },
							stdin = true,
						}
					end,
				},
				jinja = {
					function()
						return {
							exe = "djlint",
							args = { "--reformat", "-" },
							stdin = true,
						}
					end,
				},
			},
		})

		-- Format on save
		vim.api.nvim_create_autocmd("BufWritePre", {
			callback = function()
				vim.cmd("FormatWrite")
			end,
		})
	end,
}
