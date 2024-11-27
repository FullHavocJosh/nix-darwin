return {
    {
        "jose-elias-alvarez/typescript.nvim",
        dependencies = { "neovim/nvim-lspconfig" },
        config = function()
            local lspconfig = require("lspconfig")
            local capabilities = require("cmp_nvim_lsp").default_capabilities()

            -- Use ts_ls directly
            lspconfig.ts_ls.setup({
                capabilities = capabilities,
                on_attach = function(client, bufnr)
                    -- Define TypeScript-specific keybindings
                    local bufopts = { noremap = true, silent = true, buffer = bufnr }
                    vim.keymap.set("n", "gd", vim.lsp.buf.definition, bufopts)
                    vim.keymap.set("n", "K", vim.lsp.buf.hover, bufopts)
                    vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, bufopts)
                    vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, bufopts)

                    -- TypeScript.nvim specific actions
                    vim.keymap.set("n", "<leader>rf", ":TypescriptRenameFile<CR>", bufopts)
                    vim.keymap.set("n", "<leader>oi", ":TypescriptOrganizeImports<CR>", bufopts)
                end,
            })

            -- Optional: Custom commands for TypeScript actions if `typescript.nvim` fails
            vim.api.nvim_create_user_command("TypescriptRenameFile", function()
                print("This command depends on typescript.nvim.")
            end, {})
            vim.api.nvim_create_user_command("TypescriptOrganizeImports", function()
                print("This command depends on typescript.nvim.")
            end, {})
        end,
    },
}
