vim.g.have_nerd_font = true

-- herdr's dev/devim aliases launch several nvim instances at once (one per
-- workspace tab), and they all share the default main.shada file -- writing
-- marks/history on startup or exit collides across instances and nvim exits
-- immediately with E137, leaving the tab sitting at a bare shell prompt. Give
-- each project its own shada file so concurrent instances never collide.
local project = vim.fn.fnamemodify(vim.fn.getcwd(), ":t")
vim.opt.shadafile = vim.fn.stdpath("state") .. "/shada/" .. project .. ".shada"

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
