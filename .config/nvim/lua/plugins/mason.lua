return {
    {
        "williamboman/mason.nvim",
        config = function()
            require("mason").setup()
        end,
    },
    {
        "williamboman/mason-lspconfig.nvim",
        dependencies = { "williamboman/mason.nvim" },
        config = function()
            require("mason-lspconfig").setup({
                ensure_installed = {}, -- LSP servers managed by brew
                automatic_installation = false,
            })
        end,
    },
    {
        "WhoIsSethDaniel/mason-tool-installer.nvim",
        dependencies = { "williamboman/mason.nvim" },
        config = function()
            require("mason-tool-installer").setup({
                ensure_installed = {
                    "shfmt",         -- Bash formatter
                    "shellcheck",    -- Bash linter
                    "yamllint",      -- YAML linter
                    "prettier",      -- JSON formatter
                    "stylua",        -- Lua formatter
                    "tflint",        -- Terraform Linter
                    "eslint_d",      -- JavaScript/TypeScript linter
                    "black",         -- Python formatter
                },
                auto_update = true,
                run_on_start = true,
            })
        end,
    },
    --{
    --    "jay-babu/mason-null-ls.nvim",
    --    event = { "BufReadPre", "BufNewFile" },
    --    dependencies = {
    --        "williamboman/mason.nvim",
    --        "nvimtools/none-ls.nvim",
    --    },
    --    config = function()
    --        require("mason-null-ls").setup({
    --            ensure_installed = {
    --                "shfmt",         -- Bash formatter
    --                "shellcheck",    -- Bash linter
    --                "yamllint",      -- YAML linter
    --                "prettier",      -- JSON formatter
    --                "stylua",        -- Lua formatter
    --                "tflint",        -- Terraform Linter
    --                "eslint_d",
    --                "black",
    --            }, -- Tools to install
    --            automatic_installation = true,
    --        })
    --    end,
    --},
}
