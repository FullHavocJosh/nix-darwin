return {
    {
        "windwp/nvim-ts-autotag", -- Plugin for auto-closing and auto-renaming tags
        event = "InsertEnter", -- Lazy load when entering insert mode
        dependencies = { "nvim-treesitter/nvim-treesitter" }, -- Ensure Treesitter is installed
        config = function()
            require("nvim-ts-autotag").setup({
                filetypes = {
                    -- Relevant file types for your workflow
                    "json",        -- JSON for structured data
                    "yaml",        -- YAML (e.g., Ansible playbooks)
                    "toml",        -- TOML configuration files
                    "lua",         -- Lua scripts
                    "nix",         -- Nix configuration
                    "html",        -- HTML for templates or web work
                    "terraform",   -- Terraform HCL for infrastructure as code
                },
            })
        end,
    },
}
