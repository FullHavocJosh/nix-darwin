return {
	"nvim-treesitter/nvim-treesitter",
	build = ":TSUpdate", -- Automatically run `:TSUpdate` after installation
	event = "VeryLazy", -- Load early to prevent highlighting issues
	transparent = true,
	config = function()
		local configs = require("nvim-treesitter.configs")
		configs.setup({
			ensure_installed = {
				"dockerfile", -- Docker
				"gitignore", -- GitIgnore
				"bash", -- Bash
				"yaml", -- YAML
				"json", -- JSON
				"lua", -- Lua
				"hcl", -- HCL
				"terraform", -- Terraform
				"nix", -- Nix
				"toml", -- TOML
			}, -- List of parsers to install
			sync_install = false, -- Install parsers asynchronously
			auto_install = true, -- Automatically install missing parsers
			highlight = {
				enable = true, -- Enable syntax highlighting
				additional_vim_regex_highlighting = true, -- Enable both treesitter and vim syntax
			},
			indent = {
				enable = true, -- Enable automatic indentation
			},
			autotag = {
				enable = true, -- Enable automatic tagging
			},
		})
	end,
}
