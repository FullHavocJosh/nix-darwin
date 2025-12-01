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
          -- === FORMATTERS ===
          -- Shell
          "shfmt", -- Bash/Shell formatter

          -- Configuration files
          "prettier", -- JSON/YAML/JS/TS/Markdown formatter
          "taplo", -- TOML formatter

          -- Programming languages
          "stylua", -- Lua formatter
          "black", -- Python formatter
          "gofumpt", -- Go formatter (stricter than gofmt)
          "goimports", -- Go imports formatter
          "rubocop", -- Ruby formatter and linter

          -- Templates
          "djlint", -- Jinja2 template formatter

          -- SQL
          "sqlfluff", -- SQL formatter and linter

          -- === LINTERS ===
          -- Shell
          "shellcheck", -- Bash/Shell linter

          -- Configuration files
          "yamllint", -- YAML linter
          "jsonlint", -- JSON linter

          -- Programming languages
          "luacheck", -- Lua linter
          "ruff", -- Python linter (fast, replaces flake8, pylint, etc.)
          "mypy", -- Python type checker
          "eslint_d", -- JavaScript/TypeScript linter
          "golangci-lint", -- Go meta-linter

          -- Infrastructure as Code
          "tflint", -- Terraform linter
          "tfsec", -- Terraform security scanner
          "ansible-lint", -- Ansible linter

          -- Docker
          "hadolint", -- Dockerfile linter

          -- Markup
          "markdownlint", -- Markdown linter

          -- === LSP SERVERS ===
          -- Shell
          "bash-language-server",

          -- Configuration files
          "yaml-language-server",
          "json-lsp",

          -- Programming languages
          "lua-language-server",
          "pyright", -- Python LSP
          "typescript-language-server",
          "gopls", -- Go LSP

          -- Infrastructure as Code
          "terraform-ls",
          "ansible-language-server",

          -- Docker
          "dockerfile-language-server",
          "docker-compose-language-service",

          -- Markup
          "marksman", -- Markdown LSP

          -- Ruby
          "solargraph",

          -- XML
          "lemminx",

          -- PowerShell (if on macOS/Linux with pwsh)
          -- "powershell-editor-services",
        },
        auto_update = false,
        run_on_start = false,
      })
    end,
  },
}
