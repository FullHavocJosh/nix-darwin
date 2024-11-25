-- ~/.config/nvim/lua/custom/config.lua

-- nvim-tree configuration
require("nvim-tree").setup({
  git = {
    enable = true, -- Enable git integration
  },
  view = {
    adaptive_size = true, -- Adjusts the size of the tree dynamically
    width = 40, -- Set the file tree width
  },
  actions = {
    change_dir = {
      enable = true, -- Automatically update the working directory
      global = true, -- Apply to all windows
    },
  },
  renderer = {
    group_empty = true, -- Group empty directories
  },
  hijack_directories = {
    enable = true, -- Automatically change to the directory of the current file
    auto_open = true, -- Automatically open the file tree for the current directory
  },
  filters = {
    dotfiles = false, -- Don't hide dotfiles
  },
  diagnostics = {
    enable = true, -- Show diagnostics in the file tree
    icons = {
      hint = "",
      info = "",
      warning = "",
      error = "",
    },
  },
  respect_buf_cwd = true, -- Respect buffer's current working directory
})

