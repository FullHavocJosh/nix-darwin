-- Override LazyVim's conform.nvim config to add your custom formatters
return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      -- Your custom formatters (merged with LazyVim's defaults)
      bash = { "shfmt" },
      sh = { "shfmt" },
      yaml = { "prettier" },
      json = { "prettier" },
      lua = { "stylua" },
      python = { "black" },
      terraform = { "terraform_fmt" },
      tf = { "terraform_fmt" },
      ruby = { "rubocop" },
      xml = { "xmllint" },
      toml = { "taplo" },
      jinja = { "djlint" },
    },
    formatters = {
      shfmt = {
        prepend_args = { "-i", "2" },
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
    },
  },
}
