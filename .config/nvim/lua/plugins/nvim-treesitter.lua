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

		-- Periodic treesitter refresh (every 60 seconds)
		local timer = vim.loop.new_timer()
		timer:start(
			60000, -- Start after 60 seconds
			60000, -- Repeat every 60 seconds
			vim.schedule_wrap(function()
				-- Only refresh if buffer is valid and uses treesitter
				local buf = vim.api.nvim_get_current_buf()
				if vim.api.nvim_buf_is_valid(buf) then
					local ft = vim.bo[buf].filetype
					-- List of filetypes that should auto-refresh
					local refresh_filetypes = {
						"terraform",
						"hcl",
						"lua",
						"bash",
						"yaml",
						"json",
						"nix",
						"dockerfile",
					}
					for _, refresh_ft in ipairs(refresh_filetypes) do
						if ft == refresh_ft then
							-- Silently re-enable highlighting
							pcall(vim.cmd, "TSBufEnable highlight")
							break
						end
					end
				end
			end)
		)
	end,
}
