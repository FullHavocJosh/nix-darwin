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

-- TFLint on write
vim.api.nvim_create_autocmd("BufWritePost", {
  pattern = "*.tf",
  callback = function()
    vim.cmd("lua vim.lsp.buf.format()") -- Auto-format using LSP
  end,
})

-- determine sizing
local function set_custom_layout()
  local total_width = vim.o.columns

  -- Calculate split sizes
  local terminal_width = math.floor(total_width * 0.5) -- 50% for terminal
  local main_width = total_width - terminal_width      -- Remaining for main editor

  -- Open a terminal split
  vim.cmd("vsplit")
  vim.cmd("vertical resize " .. terminal_width) -- Resize terminal split
  vim.cmd("terminal")

  -- Move back to the main editing window
  vim.cmd("wincmd h")
  vim.cmd("resize " .. main_width) -- Resize main editor
end

-- Apply layout on startup
vim.api.nvim_create_autocmd("VimEnter", {
  callback = set_custom_layout,
})

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

