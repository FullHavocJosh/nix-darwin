vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

require("config.lazy")
require("config.options")
require("config.keymaps")
require("config.filetype")
require("config.neovide")

vim.cmd.colorscheme("catppuccin")

-- Apply transparency after colorscheme
vim.defer_fn(function()
	local transparency_file = vim.fn.stdpath("config") .. "/plugin/after/transparency.lua"
	if vim.fn.filereadable(transparency_file) == 1 then
		dofile(transparency_file)
	end
end, 100)
