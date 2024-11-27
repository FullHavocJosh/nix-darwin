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
                ensure_installed = {
                    "bashls",        -- Bash
                    "yamlls",        -- Ansible YAML
                    "jsonls",        -- JSON
                    "lua_ls",        -- Lua
                    "terraformls",   -- Terraform
                    "tflint",        -- Terraform Linter
                    "rnix",          -- Nix
                    "powershell_es", -- PowerShell
                }, -- List of servers to install
                automatic_installation = true,
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
            -- Autocommands for linters and formatters
            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.sh",
                callback = function()
                    vim.fn.system("shellcheck " .. vim.fn.expand("%")) -- Run shellcheck on Bash files
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.sh",
                callback = function()
                    vim.fn.system("shfmt -i 2 -w " .. vim.fn.expand("%")) -- Format Bash files with shfmt
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.yaml,*.yml",
                callback = function()
                    vim.fn.system("yamllint " .. vim.fn.expand("%")) -- Lint YAML files with yamllint
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.yaml,*.yml",
                callback = function()
                    vim.fn.system("prettier --write " .. vim.fn.expand("%")) -- Format YAML files with Prettier
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.json",
                callback = function()
                    vim.fn.system("prettier --write " .. vim.fn.expand("%")) -- Format JSON files with Prettier
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.lua",
                callback = function()
                    vim.fn.system("stylua " .. vim.fn.expand("%")) -- Format Lua files with Stylua
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.py",
                callback = function()
                    vim.fn.system("black " .. vim.fn.expand("%")) -- Format Python files with Black
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.tf",
                callback = function()
                    vim.fn.system("terraform fmt " .. vim.fn.expand("%")) -- Format Terraform files with Terraform fmt
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.tf",
                callback = function()
                    vim.fn.system("tflint " .. vim.fn.expand("%")) -- Lint Terraform files with TFLint
                end,
            })

            vim.api.nvim_create_autocmd("BufWritePost", {
                pattern = "*.ts,*.js",
                callback = function()
                    vim.fn.system("eslint_d " .. vim.fn.expand("%")) -- Lint JavaScript/TypeScript files with eslint_d
                end,
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
