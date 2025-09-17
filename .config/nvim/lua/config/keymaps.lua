local keymap = vim.keymap

vim.g.mapleader = " "

---------------------
-- General Keymaps
---------------------

-- Use Cmd+Z for undo
vim.api.nvim_set_keymap("n", "<D-z>", "u", { noremap = true, silent = true })
vim.api.nvim_set_keymap("i", "<D-z>", "<C-o>u", { noremap = true, silent = true })

-- Use Cmd+R for redo
vim.api.nvim_set_keymap("n", "<D-r>", "<C-r>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("i", "<D-r>", "<C-o><C-r>", { noremap = true, silent = true })

-- Use jk to exit insert mode
-- keymap.set("i", "jk", "<ESC>")

-- Clear search highlights
-- keymap.set("n", "<leader>nh", ":nohl<CR>")

-- Delete single character without copying into register
-- keymap.set("n", "x", '"_x')

-- Increment/decrement numbers
keymap.set("n", "<leader>+", "<C-a>") -- Increment
keymap.set("n", "<leader>-", "<C-x>") -- Decrement

-- Window management
-- keymap.set("n", "<leader>sv", "<C-w>v") -- Split window vertically
-- keymap.set("n", "<leader>sh", "<C-w>s") -- Split window horizontally
-- keymap.set("n", "<leader>se", "<C-w>=") -- Make split windows equal width & height
-- keymap.set("n", "<leader>sx", ":close<CR>") -- Close current split window

-- keymap.set("n", "<leader>to", ":tabnew<CR>") -- Open new tab
-- keymap.set("n", "<leader>tx", ":tabclose<CR>") -- Close current tab
-- keymap.set("n", "<leader>tn", ":tabn<CR>") --  Go to next tab
-- keymap.set("n", "<leader>tp", ":tabp<CR>") --  Go to previous tab

----------------------
-- Plugin Keybinds
----------------------

-- Vim-maximizer
-- keymap.set("n", "<leader>sm", ":MaximizerToggle<CR>") -- Toggle split window maximization

-- Nvim-tree
keymap.set("n", "<leader>e", ":NvimTreeFocus<CR>") -- Focus file explorer (opens if closed)
keymap.set("n", "<leader>E", ":NvimTreeToggle<CR>") -- Toggle file explorer (open/close)

-- Telescope
keymap.set("n", "<leader>f", "<cmd>Telescope find_files<cr>") -- Find files within current working directory, respects .gitignore
-- keymap.set("n", "<leader>fs", "<cmd>Telescope live_grep<cr>") -- Find string in current working directory as you type
-- keymap.set("n", "<leader>fc", "<cmd>Telescope grep_string<cr>") -- Find string under cursor in current working directory
keymap.set("n", "<leader>b", "<cmd>Telescope buffers<cr>") -- List open buffers in current neovim instance
keymap.set("n", "<leader>h", "<cmd>Telescope help_tags<cr>") -- List available help tags

-- Telescope git commands
-- keymap.set("n", "<leader>gc", "<cmd>Telescope git_commits<cr>") -- List all git commits (use <cr> to checkout) ["gc" for git commits
keymap.set("n", "<leader>gc", "<cmd>Telescope git_bcommits<cr>") -- List git commits for current file/buffer (use <cr> to checkout) ["gfc" for git file commits
-- keymap.set("n", "<leader>gb", "<cmd>Telescope git_branches<cr>") -- List git branches (use <cr> to checkout) ["gb" for git branch]
keymap.set("n", "<leader>gs", "<cmd>Telescope git_status<cr>") -- List current changes per file with diff preview ["gs" for git status]

-- LSP Keybinds
keymap.set("n", "gd", "<cmd>Lspsaga goto_definition<CR>") -- Go to definition
keymap.set("n", "K", "<cmd>Lspsaga hover_doc<CR>") -- Show hover documentation
keymap.set("n", "<leader>ca", "<cmd>Lspsaga code_action<CR>") -- Code actions
keymap.set("n", "<leader>rn", "<cmd>Lspsaga rename<CR>") -- Rename symbol
keymap.set("n", "<leader>d", "<cmd>Lspsaga show_line_diagnostics<CR>") -- Show line diagnostics

-- Spectre (Find and Replace)
keymap.set("n", "<leader>s", '<cmd>lua require("spectre").toggle()<CR>') -- Toggle Spectre
keymap.set("n", "<leader>sw", '<cmd>lua require("spectre").open_visual({select_word=true})<CR>') -- Search current word
keymap.set("v", "<leader>sw", '<esc><cmd>lua require("spectre").open_visual()<CR>') -- Search current selection
keymap.set("n", "<leader>sp", '<cmd>lua require("spectre").open_file_search({select_word=true})<CR>') -- Search in current file

-- Buffer navigation
keymap.set("n", "<leader>x", ":bdelete<CR>") -- Close current buffer
keymap.set("n", "<Tab>", ":BufferLineCycleNext<CR>") -- Next buffer
keymap.set("n", "<S-Tab>", ":BufferLineCyclePrev<CR>") -- Previous buffer
keymap.set("n", "<leader>1", ":BufferLineGoToBuffer 1<CR>") -- Go to buffer 1
keymap.set("n", "<leader>2", ":BufferLineGoToBuffer 2<CR>") -- Go to buffer 2
keymap.set("n", "<leader>3", ":BufferLineGoToBuffer 3<CR>") -- Go to buffer 3
keymap.set("n", "<leader>4", ":BufferLineGoToBuffer 4<CR>") -- Go to buffer 4
keymap.set("n", "<leader>5", ":BufferLineGoToBuffer 5<CR>") -- Go to buffer 5

-- Tmux integration - pass through Ctrl+t to tmux
keymap.set("n", "<C-t>", "<C-t>", { noremap = false, silent = true })


