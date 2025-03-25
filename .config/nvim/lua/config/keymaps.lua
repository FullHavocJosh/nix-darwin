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
keymap.set("n", "<leader>e", ":NvimTreeToggle<CR>") -- Toggle file explorer

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

-- Comment
-- keymap.set(
--	"n",
--	"<D-/>",
--	'<cmd>lua require("Comment.api").toggle.linewise.current()<CR>',
--	{ desc = "Toggle comment for the current line" }
-- )
-- keymap.set(
--	"v",
--	"<D-/>",
--	'<ESC><cmd>lua require("Comment.api").toggle.linewise(vim.fn.visualmode())<CR>',
--	{ desc = "Toggle comment for selected lines" }
-- )
