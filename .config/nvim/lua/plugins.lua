-- ~/.config/nvim/lua/custom/plugins.lua
return {
  -- Catppuccin Theme Plugin
  {
    "catppuccin/nvim",
    name = "catppuccin",
    config = function()
      require("catppuccin").setup({})
    end,
  },
}

