return {
  {
    "mason-org/mason.nvim",
    config = function()
      require("mason").setup()
    end,
  },
  {
    "mason-org/mason-lspconfig.nvim",
    dependencies = { "mason-org/mason.nvim" },
    config = function()
      require("mason-lspconfig").setup({
        ensure_installed = {}, -- LSP servers managed by brew
        automatic_installation = false,
      })
    end,
  },
  {
    "WhoIsSethDaniel/mason-tool-installer.nvim",
    dependencies = { "mason-org/mason.nvim" },
    config = function()
      require("mason-tool-installer").setup({
        ensure_installed = {
          -- Formatters
          "shfmt",
          "prettier",
          "taplo",
          "stylua",
          "black",
          "gofumpt",
          "goimports",
          "rubocop",
          "djlint",
          "sqlfluff",

          -- Linters
          "shellcheck",
          "yamllint",
          "jsonlint",
          "luacheck",
          "ruff",
          "mypy",
          "eslint_d",
          "golangci-lint",
          "tflint",
          "tfsec",
          "ansible-lint",
          "hadolint",
          "markdownlint",

          -- LSP servers
          "bash-language-server",
          "yaml-language-server",
          "json-lsp",
          "lua-language-server",
          "pyright",
          "typescript-language-server",
          "gopls",
          "terraform-ls",
          "ansible-language-server",
          "dockerfile-language-server",
          "docker-compose-language-service",
          "marksman",
          "solargraph",
          "lemminx",
        },
        auto_update = false,
        run_on_start = false,
      })
    end,
  },
}
