return {
    {
        "windwp/nvim-ts-autotag",
        event = { "InsertEnter" }, -- Load on entering insert mode
        dependencies = { "nvim-treesitter/nvim-treesitter" }, -- Ensure Treesitter is installed
        config = function()
            require("nvim-ts-autotag").setup({
                filetypes = {
                    "html",
                    "javascript",
                    "typescript",
                    "javascriptreact",
                    "typescriptreact",
                    "vue",
                    "svelte",
                    "xml",
                },
            })
        end,
    },
}
