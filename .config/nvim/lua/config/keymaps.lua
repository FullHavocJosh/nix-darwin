-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local keymap = vim.keymap

---------------------
-- General Keymaps
---------------------

-- Fix syntax highlighting issues (for when treesitter stops working)
keymap.set("n", "<leader>fs", ":TSBufEnable highlight<CR>", { desc = "Fix Syntax highlighting" })

-- Use Cmd+Z for undo
vim.api.nvim_set_keymap("n", "<D-z>", "u", { noremap = true, silent = true })
vim.api.nvim_set_keymap("i", "<D-z>", "<C-o>u", { noremap = true, silent = true })

-- Use Cmd+R for redo
vim.api.nvim_set_keymap("n", "<D-r>", "<C-r>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("i", "<D-r>", "<C-o><C-r>", { noremap = true, silent = true })

-- Window management (moved increment/decrement to avoid conflicts)
keymap.set("n", "<leader>wv", "<C-w>v", { desc = "Split window vertically" })
keymap.set("n", "<leader>wh", "<C-w>s", { desc = "Split window horizontally" })
keymap.set("n", "<leader>w=", "<C-w>=", { desc = "Make split windows equal width & height" })
keymap.set("n", "<leader>wc", ":close<CR>", { desc = "Close current split window" })
keymap.set("n", "<leader>w+", "<C-w>+", { desc = "Increase split height" })
keymap.set("n", "<leader>w-", "<C-w>-", { desc = "Decrease split height" })

----------------------
-- Plugin Keybinds
----------------------

-- Neo-tree keybindings (centralized - duplicates removed from plugin config)
keymap.set("n", "<leader>e", ":Neotree toggle float<CR>", { desc = "Toggle Neo-tree (floating)" })
keymap.set("n", "<leader>o", ":Neotree filesystem reveal left<CR>", { desc = "Reveal current file in Neo-tree" })
keymap.set("n", "<leader>b", ":Neotree buffers reveal float<CR>", { desc = "Show buffers in Neo-tree" })
keymap.set("n", "<leader>gs", ":Neotree git_status<CR>", { desc = "Show git status in Neo-tree" })

-- Telescope (LazyVim default, but keeping explicit for clarity)
keymap.set("n", "<leader>ff", "<cmd>Telescope find_files<cr>", { desc = "Find files" })
keymap.set("n", "<leader>fg", "<cmd>Telescope live_grep<cr>", { desc = "Find string (live grep)" })
keymap.set("n", "<leader>fh", "<cmd>Telescope help_tags<cr>", { desc = "Find help tags" })

-- Telescope git commands (if Telescope git integration is available)
keymap.set("n", "<leader>gc", "<cmd>Telescope git_bcommits<cr>", { desc = "Git commits for current buffer" })

-- LSP Keybinds (LSPSaga)
keymap.set("n", "gd", "<cmd>Lspsaga goto_definition<CR>", { desc = "Go to definition" })
keymap.set("n", "K", "<cmd>Lspsaga hover_doc<CR>", { desc = "Show hover documentation" })
keymap.set("n", "<leader>ca", "<cmd>Lspsaga code_action<CR>", { desc = "Code actions" })
keymap.set("n", "<leader>rn", "<cmd>Lspsaga rename<CR>", { desc = "Rename symbol" })
keymap.set("n", "<leader>d", "<cmd>Lspsaga show_line_diagnostics<CR>", { desc = "Show line diagnostics" })

-- Spectre (Find and Replace) - using plugin's configured keybindings
-- <leader>sr - Toggle Spectre
-- <leader>sw - Search current word
-- <leader>sp - Search in current file

-- Buffer navigation (simplified without bufferline)
keymap.set("n", "<leader>x", ":bdelete<CR>", { desc = "Close current buffer" })
keymap.set("n", "<Tab>", ":bnext<CR>", { desc = "Next buffer" })
keymap.set("n", "<S-Tab>", ":bprevious<CR>", { desc = "Previous buffer" })

-- Tmux integration - pass through Ctrl+t to tmux
keymap.set("n", "<C-t>", "<C-t>", { noremap = false, silent = true })
