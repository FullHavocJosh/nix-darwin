-- Fix for cmp_luasnip after/plugin loading before nvim-cmp
-- This prevents the after/plugin file from loading during startup
-- We manually register it in nvim-cmp's config instead

-- Disable the after/plugin for cmp_luasnip
vim.g.loaded_cmp_luasnip = 1
