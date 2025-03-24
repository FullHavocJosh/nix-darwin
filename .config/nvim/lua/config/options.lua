local opt = vim.opt

-- Line numbering
opt.relativenumber = false
opt.number = true

-- Tabs and indents
opt.tabstop = 2
opt.shiftwidth = 2
opt.expandtab = true
opt.autoindent = true

-- Line wrap
opt.wrap = true

-- Searching
opt.ignorecase = true
opt.smartcase = true

-- Cursor
opt.cursorline = true

-- Appearance
opt.termguicolors = true
opt.signcolumn = "yes"

-- Backspace
opt.backspace = "indent,eol,start"

-- Clipboard
opt.clipboard:append("unnamedplus")

-- Splitting windows
opt.splitright = true
opt.splitbelow = true

opt.iskeyword:append("-")

-- Optionally enable 24-bit color
opt.termguicolors = true
