-- Fix treesitter jsonc issue early (before plugins load)
vim.treesitter.language.register("json", "jsonc")

-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")
