return {
    {
        "glepnir/lspsaga.nvim",
        branch = "main",
        dependencies = {
            "nvim-tree/nvim-web-devicons",
            "nvim-treesitter/nvim-treesitter",
        },
        config = function()
            -- Safely import lspsaga
            local saga_status, saga = pcall(require, "lspsaga")
            if not saga_status then
                return
            end

            saga.setup({
                -- Keybinds for navigation in lspsaga window
                scroll_preview = { scroll_down = "<C-f>", scroll_up = "<C-b>" },
                -- Use Enter to open file with definition preview
                definition = {
                    edit = "<CR>",
                },
                -- UI customization
                ui = {
                    colors = {
                        normal_bg = "#022746",
                    },
                    border = "rounded", -- Rounded borders for windows
                },
                -- Enable symbol in winbar
                symbol_in_winbar = {
                    enable = true,
                },
            })
        end,
    },
}
