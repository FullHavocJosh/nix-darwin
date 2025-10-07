-- Line numbering
vim.opt.relativenumber = false
vim.opt.number = true

-- Tabs and indents
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.autoindent = true

-- Line wrap
vim.opt.wrap = true

-- Searching
vim.opt.ignorecase = true
vim.opt.smartcase = true

-- Appearance
vim.opt.termguicolors = true
vim.opt.signcolumn = "yes"

-- Cursor
vim.opt.guicursor = {
	"n:block-nCursor",
	"i:ver25-iCursor",
	"v:block-vCursor",
}

-- Backspace
vim.opt.backspace = "indent,eol,start"

-- Clipboard
vim.opt.clipboard:append("unnamedplus")

-- Autoreload files
vim.opt.autoread = true

-- Auto-refresh settings for better responsiveness
vim.opt.updatetime = 250  -- Faster CursorHold events
vim.opt.timeout = true
vim.opt.timeoutlen = 300

-- Auto-refresh on focus/buffer enter (skip if in insert mode)
vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
  pattern = "*",
  command = "if mode() != 'c' && mode() != 'i' | checktime | endif",
})

-- Splitting windows
vim.opt.splitright = true
vim.opt.splitbelow = true

vim.opt.iskeyword:append("-")

-- Command line height
vim.opt.cmdheight = 0
