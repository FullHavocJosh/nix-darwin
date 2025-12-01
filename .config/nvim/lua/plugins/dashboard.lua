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

    -- Function to get git repo info
    local function get_git_info()
      local git_dir = vim.fn.finddir(".git", vim.fn.getcwd() .. ";")
      if git_dir ~= "" then
        -- Get repo name from remote URL or directory name
        local remote = vim.fn.system("git config --get remote.origin.url 2>/dev/null")
        local repo_name

        if remote and remote ~= "" then
          -- Extract repo name from URL (handles both https and ssh)
          repo_name = remote:match("([^/]+)%.git") or remote:match("([^/]+)$")
          repo_name = repo_name:gsub("\n", "")
        else
          -- Fallback to directory name
          repo_name = vim.fn.fnamemodify(vim.fn.getcwd(), ":t")
        end

        -- Get current branch
        local branch = vim.fn.system("git branch --show-current 2>/dev/null"):gsub("\n", "")

        if branch ~= "" then
          return string.format("  %s  %s", repo_name, branch)
        else
          return string.format("  %s", repo_name)
        end
      end
      return ""
    end

    -- Build header with git info
    local git_info = get_git_info()
    local header_text = [[
 ███╗   ██╗███████╗ ██████╗ ██╗   ██╗██╗███╗   ███╗
 ████╗  ██║██╔════╝██╔═══██╗██║   ██║██║████╗ ████║
 ██╔██╗ ██║█████╗  ██║   ██║██║   ██║██║██╔████╔██║
 ██║╚██╗██║██╔══╝  ██║   ██║╚██╗ ██╔╝██║██║╚██╔╝██║
 ██║ ╚████║███████╗╚██████╔╝ ╚████╔╝ ██║██║ ╚═╝ ██║
 ╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═══╝  ╚═╝╚═╝     ╚═╝
]]
    if git_info ~= "" then
      header_text = header_text .. "\n" .. git_info .. "\n"
    end

    return {
      dashboard = {
        enabled = true,
        preset = {
          header = header_text,
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
