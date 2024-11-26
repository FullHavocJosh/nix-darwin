vim.g.base46_cache = vim.fn.stdpath "data" .. "/base46/"
vim.g.mapleader = " "

-- bootstrap lazy and all plugins
local lazypath = vim.fn.stdpath "data" .. "/lazy/lazy.nvim"

if not vim.uv.fs_stat(lazypath) then
  local repo = "https://github.com/folke/lazy.nvim.git"
  vim.fn.system { "git", "clone", "--filter=blob:none", repo, "--branch=stable", lazypath }
end

vim.opt.rtp:prepend(lazypath)
vim.opt.clipboard:append("unnamedplus")

local lazy_config = require "configs.lazy"

-- load plugins
require("lazy").setup({
  {
    "NvChad/NvChad",
    lazy = false,
    branch = "v2.5",
    import = "nvchad.plugins",
  },

  { import = "plugins" },
}, lazy_config)

-- load theme
dofile(vim.g.base46_cache .. "defaults")
dofile(vim.g.base46_cache .. "statusline")

require "options"
require "nvchad.autocmds"

vim.schedule(function()
  require "mappings"
end)

vim.api.nvim_create_autocmd("VimEnter", {
  callback = function()
    -- Open NvimTree only if no file or directory is provided as an argument
    if #vim.fn.argv() == 0 then
      vim.cmd("NvimTreeToggle")
    end
  end,
})

vim.api.nvim_create_autocmd({"BufEnter", "TermOpen"}, {
  pattern = "term://*",
  callback = function()
    vim.wo.number = false          -- Disable absolute line numbers
    vim.wo.relativenumber = false  -- Disable relative line numbers
  end,
})

vim.api.nvim_create_autocmd("BufWritePost", {
    pattern = "*.yml,*.yaml",
    callback = function()
        if vim.fn.executable("ansible-lint") == 1 then
            vim.cmd("silent !ansible-lint " .. vim.fn.expand("%"))
        else
            print("ansible-lint not installed.")
        end
    end,
})

