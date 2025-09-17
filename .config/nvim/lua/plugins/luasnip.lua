return {
    -- Snippet engine
    {
        "L3MON4D3/LuaSnip",
        dependencies = {
            "rafamadriz/friendly-snippets", -- Predefined snippets
        },
        config = function()
            local luasnip = require("luasnip")

            -- Load snippets from friendly-snippets
            require("luasnip.loaders.from_vscode").lazy_load()

            -- Optional: Keybindings for expanding and jumping in snippets
            vim.keymap.set({ "i", "s" }, "<C-f>", function()
                if luasnip.expand_or_jumpable() then
                    luasnip.expand_or_jump()
                end
            end, { silent = true })

            vim.keymap.set({ "i", "s" }, "<C-b>", function()
                if luasnip.jumpable(-1) then
                    luasnip.jump(-1)
                end
            end, { silent = true })
        end,
    },

    -- Autocompletion source for LuaSnip
    {
        "saadparwaiz1/cmp_luasnip",
    },

    -- Predefined snippets
    {
        "rafamadriz/friendly-snippets",
        lazy = true, -- Loaded only when LuaSnip is loaded
    },
}
