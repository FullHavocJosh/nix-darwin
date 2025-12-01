return {
  "folke/snacks.nvim",
  priority = 1000,
  opts = function()
    -- Use more compatible Nerd Font icons from a working Unicode range
    local icons = {
      file = "󰈔 ", -- nf-md-file_document
      new = "󰝒 ", -- nf-md-file_plus
      search = "󰱼 ", -- nf-md-text_search
      recent = "󱋢 ", -- nf-md-history
      folder = "󰉋 ", -- nf-md-folder
      config = "󰒓 ", -- nf-md-cog
      session = "󰦛 ", -- nf-md-restore
      lazy = "󰒲 ", -- nf-md-package
      quit = "󰗼 ", -- nf-md-exit_to_app
    }

    return {
      dashboard = {
        enabled = true,
        preset = {
          keys = {
            { icon = icons.file, key = "f", desc = "Find File", action = ":lua Snacks.dashboard.pick('files')" },
            { icon = icons.new, key = "n", desc = "New File", action = ":ene | startinsert" },
            { icon = icons.search, key = "g", desc = "Find Text", action = ":lua Snacks.dashboard.pick('live_grep')" },
            {
              icon = icons.recent,
              key = "r",
              desc = "Recent Files",
              action = ":lua Snacks.dashboard.pick('oldfiles')",
            },
            {
              icon = icons.folder,
              key = "e",
              desc = "Explore Current Directory",
              action = ":Neotree filesystem reveal float",
            },
            {
              icon = icons.config,
              key = "c",
              desc = "Config",
              action = ":lua Snacks.dashboard.pick('files', {cwd = vim.fn.stdpath('config')})",
            },
            { icon = icons.session, key = "s", desc = "Restore Session", section = "session" },
            { icon = icons.lazy, key = "l", desc = "Lazy", action = ":Lazy", enabled = package.loaded.lazy ~= nil },
            { icon = icons.quit, key = "q", desc = "Quit", action = ":qa" },
          },
        },
      },
    }
  end,
}
