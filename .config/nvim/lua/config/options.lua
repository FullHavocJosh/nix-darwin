-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- Line numbers
vim.opt.relativenumber = false
vim.opt.number = true

-- Indentation
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.autoindent = true

-- Line wrapping
vim.opt.wrap = true

-- Search
vim.opt.ignorecase = true
vim.opt.smartcase = true

-- Appearance
vim.opt.termguicolors = true
vim.opt.signcolumn = "yes"

-- Cursor shape
vim.opt.guicursor = {
  "n:block-nCursor",
  "i:ver25-iCursor",
  "v:block-vCursor",
}

-- Editing
vim.opt.backspace = "indent,eol,start"
vim.opt.clipboard:append("unnamedplus")

-- Auto-reload files on external changes
vim.opt.autoread = true
vim.opt.updatetime = 250

vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
  pattern = "*",
  command = "if mode() != 'c' && mode() != 'i' | checktime | endif",
})

-- Window splits
vim.opt.splitright = true
vim.opt.splitbelow = true
vim.opt.iskeyword:append("-")
vim.opt.cmdheight = 1

-- Reduce "Press ENTER" prompts and startup messages
vim.opt.shortmess:append("c") -- Don't show completion messages
vim.opt.shortmess:append("I") -- Don't show intro message
vim.opt.shortmess:append("W") -- Don't show "written" messages
vim.opt.shortmess:append("F") -- Don't show file info when editing
vim.opt.shortmess:append("A") -- Don't show "ATTENTION" messages
vim.opt.shortmess:append("s") -- Don't show "search hit BOTTOM" messages
vim.opt.shortmess:append("S") -- Don't show search count message
