local opt = vim.opt -- cleaner configs

-- line numbering
opt.relativenumber = false
opt.number = true

-- tabs and indents
opt.tabstop = 2
opt.shiftwidth = 2
opt.expandtab = true
opt.autoindent = true

-- line wrap
opt.wrap = true

-- searching
opt.ignorecase = true
opt.smartcase = true

-- cursor
opt.cursorline = true

-- appearance
opt.termguicolors = true
opt.background = "dark"
opt.signcolumn = "yes"

-- backspace
opt.backspace = "indent,eol,start"

-- clipboard
opt.clipboard:append("unnamedplus")

-- spliting windows
opt.splitright = true
opt.splitbelow = true

opt.iskeyword:append("-")

-- optionally enable 24-bit colour
opt.termguicolors = true
