return {
  "nvim-treesitter/nvim-treesitter",
  build = ":TSUpdate", -- Automatically run `:TSUpdate` after installation
  event = { "BufReadPost", "BufNewFile" }, -- Load when opening files
  transparent = true,
  config = function()
    -- Check if treesitter is available before requiring
    local status_ok, configs = pcall(require, "nvim-treesitter.configs")
    if not status_ok then
      vim.notify("nvim-treesitter not loaded yet", vim.log.levels.WARN)
      return
    end

    configs.setup({
      ensure_installed = {
        "dockerfile", -- Docker
        "gitignore", -- GitIgnore
        "bash", -- Bash
        "yaml", -- YAML
        "json", -- JSON
        "lua", -- Lua
        "hcl", -- HCL
        "terraform", -- Terraform
        "nix", -- Nix
        "toml", -- TOML
      }, -- List of parsers to install
      sync_install = false, -- Install parsers asynchronously
      auto_install = true, -- Automatically install missing parsers
      highlight = {
        enable = true, -- Enable syntax highlighting
        additional_vim_regex_highlighting = true, -- Enable both treesitter and vim syntax
      },
      indent = {
        enable = true, -- Enable automatic indentation
      },
      autotag = {
        enable = true, -- Enable automatic tagging
      },
    })
  end,
}
