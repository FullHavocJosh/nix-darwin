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

-- Splitting windows
vim.opt.splitright = true
vim.opt.splitbelow = true

vim.opt.iskeyword:append("-")

-- optionally enable 24-bit color
vim.opt.termguicolors = true
