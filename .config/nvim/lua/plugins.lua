local plugins = {
  {
    {
    "gbprod/yanky.nvim",
    config = function()
      require("yanky").setup({
        highlight = { timer = 200 },
        system_clipboard = {
          sync_with_ring = true,
        },
      })
      vim.keymap.set({ "n", "x" }, "y", "<Plug>(YankyYank)", { noremap = true })
    end,
    },
  }
}
return plugins
