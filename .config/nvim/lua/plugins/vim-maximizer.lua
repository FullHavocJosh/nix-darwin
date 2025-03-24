return {
    {
        "szw/vim-maximizer", -- Plugin repository
        config = function()
            -- Optional: You can set keybindings for vim-maximizer here
            vim.keymap.set("n", "<leader>m", ":MaximizerToggle<CR>", { silent = true, noremap = true })
        end,
    },
}
