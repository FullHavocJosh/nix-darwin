return {
	{
		"mason-org/mason.nvim",
		config = function()
			require("mason").setup()
		end,
	},
	{
		"mason-org/mason-lspconfig.nvim",
		dependencies = { "mason-org/mason.nvim" },
		config = function()
			require("mason-lspconfig").setup({
				ensure_installed = {}, -- LSP servers managed by brew
				automatic_installation = false,
			})
		end,
	},
	{
		"WhoIsSethDaniel/mason-tool-installer.nvim",
		dependencies = { "mason-org/mason.nvim" },
		config = function()
			require("mason-tool-installer").setup({
				ensure_installed = {
					"shfmt", -- Bash formatter
					"shellcheck", -- Bash linter
					"yamllint", -- YAML linter
					"prettier", -- JSON formatter
					"stylua", -- Lua formatter
					"tflint", -- Terraform Linter
					"eslint_d", -- JavaScript/TypeScript linter
					"black", -- Python formatter

					"rubocop", -- Ruby formatter and linter
					"djlint", -- Jinja2 template formatter
				},
				auto_update = false,
				run_on_start = false,
			})
		end,
	},
	--{
	--    "jay-babu/mason-null-ls.nvim",
	--    event = { "BufReadPre", "BufNewFile" },
	--    dependencies = {
	--        "williamboman/mason.nvim",
	--        "nvimtools/none-ls.nvim",
	--    },
	--    config = function()
	--        require("mason-null-ls").setup({
	--            ensure_installed = {
	--                "shfmt",         -- Bash formatter
	--                "shellcheck",    -- Bash linter
	--                "yamllint",      -- YAML linter
	--                "prettier",      -- JSON formatter
	--                "stylua",        -- Lua formatter
	--                "tflint",        -- Terraform Linter
	--                "eslint_d",
	--                "black",
	--            }, -- Tools to install
	--            automatic_installation = true,
	--        })
	--    end,
	--},
}
