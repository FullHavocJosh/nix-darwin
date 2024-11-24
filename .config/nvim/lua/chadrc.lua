-- This file needs to have same structure as nvconfig.lua 
-- https://github.com/NvChad/ui/blob/v3.0/lua/nvconfig.lua
-- Please read that file to know all available options :( 

---@type ChadrcConfig
local M = {}

-- Include your custom config
M.ui = {
  theme = "default",
  nvimtree = {
    -- Include your NvimTree settings directly here
    git = {
      enable = true,
    },
    view = {
      width = 30,
    },
  },
}

M.base46 = {
	theme = "catppuccin",
}

return M

