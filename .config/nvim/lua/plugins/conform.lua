-- Override LazyVim's conform.nvim config to add your custom formatters
return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      -- Shell scripting
      bash = { "shfmt" },
      sh = { "shfmt" },
      zsh = { "shfmt" },

      -- Configuration files
      yaml = { "prettier" },
      yml = { "prettier" },
      json = { "prettier" },
      jsonc = { "prettier" },
      toml = { "taplo" },
      xml = { "xmllint" },

      -- Programming languages
      lua = { "stylua" },
      python = { "ruff_format", "black" },
      javascript = { "prettier" },
      javascriptreact = { "prettier" },
      typescript = { "prettier" },
      typescriptreact = { "prettier" },
      go = { "gofmt", "goimports" },
      ruby = { "rubocop" },

      -- Infrastructure as Code
      terraform = { "terraform_fmt" },
      tf = { "terraform_fmt" },
      hcl = { "terraform_fmt" },

      -- Templates
      jinja = { "djlint" },
      ["jinja.html"] = { "djlint" },
      htmldjango = { "djlint" },

      -- Markup
      markdown = { "prettier", "markdownlint" },
      ["markdown.mdx"] = { "prettier" },

      -- SQL
      sql = { "sqlfluff" },

      -- PowerShell (if formatter available)
      ps1 = { "powershell_fmt" },
      psm1 = { "powershell_fmt" },
    },
    formatters = {
      shfmt = {
        prepend_args = { "-i", "2", "-ci" },
      },
      terraform_fmt = {
        command = "terraform",
        args = { "fmt", "-" },
        stdin = true,
      },
      xmllint = {
        command = "xmllint",
        args = { "--format", "-" },
        stdin = true,
      },
      djlint = {
        command = "djlint",
        args = { "--reformat", "-" },
        stdin = true,
      },
      sqlfluff = {
        command = "sqlfluff",
        args = { "fix", "--dialect", "postgres", "-" },
        stdin = true,
      },
      markdownlint = {
        command = "markdownlint",
        args = { "--fix", "$FILENAME" },
        stdin = false,
      },
      -- PowerShell formatter (custom - may need adjustment based on availability)
      powershell_fmt = {
        command = "pwsh",
        args = { "-NoProfile", "-Command", "Invoke-Formatter", "-ScriptDefinition", "$input" },
        stdin = true,
      },
    },
  },
}
