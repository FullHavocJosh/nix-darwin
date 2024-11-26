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
  {
    "jose-elias-alvarez/null-ls.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    lazy = false, -- Ensure it loads immediately
  },
  {
    "pearofducks/ansible-vim",
    ft = { "yaml", "yml" }, -- Load for YAML files
    lazy = false, -- Ensure it loads immediately
  },
}

