return {
    {
        "lewis6991/gitsigns.nvim", -- Plugin for Git signs and integrations
        event = { "BufReadPre", "BufNewFile" }, -- Load lazily for git-tracked files
        dependencies = { "nvim-lua/plenary.nvim" }, -- Required dependency
        config = true, -- Use the default configuration
    },
}
