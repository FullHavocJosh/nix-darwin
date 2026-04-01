vim.g.have_nerd_font = true

vim.opt.encoding = "utf-8"
vim.opt.fileencoding = "utf-8"

vim.opt.relativenumber = false
vim.opt.number = true

vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.autoindent = true

vim.opt.wrap = true

vim.opt.ignorecase = true
vim.opt.smartcase = true

vim.opt.termguicolors = true
vim.opt.signcolumn = "yes"

vim.opt.guicursor = {
  "n:block-nCursor",
  "i:ver25-iCursor",
  "v:block-vCursor",
}

vim.opt.backspace = "indent,eol,start"
vim.opt.clipboard:append("unnamedplus")

vim.opt.autoread = true
vim.opt.updatetime = 250 -- CursorHold delay for diagnostic popup

vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
  pattern = "*",
  command = "if mode() != 'c' && mode() != 'i' | checktime | endif",
})

vim.opt.splitright = true
vim.opt.splitbelow = true
vim.opt.iskeyword:append("-")
vim.opt.cmdheight = 1

vim.opt.shortmess:append("c")
vim.opt.shortmess:append("I")
vim.opt.shortmess:append("W")
vim.opt.shortmess:append("F")
vim.opt.shortmess:append("A")
vim.opt.shortmess:append("s")
vim.opt.shortmess:append("S")
