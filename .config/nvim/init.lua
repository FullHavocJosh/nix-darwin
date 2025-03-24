require("config.lazy")
require("config.options")
require("config.keymaps")

vim.cmd.colorscheme("catppuccin")

-- Disable netrw at the very start of your init.lua
vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

vim.g.transparent_groups = vim.list_extend(
		vim.g.transparent_groups or {},
	vim.tbl_map(function(v)
		return v.hl_group
	end, vim.tbl_values(require("bufferline.config").highlights))
)
