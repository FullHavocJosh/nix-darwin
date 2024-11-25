-- Load NVChad defaults
require("nvchad.configs.lspconfig").defaults()

local lspconfig = require "lspconfig"
local null_ls = require("null-ls")
local nvlsp = require "nvchad.configs.lspconfig"

-- LSP Servers list
local servers = { "html", "cssls", "terraformls" } -- Add terraformls

-- Configure LSPs
for _, lsp in ipairs(servers) do
  lspconfig[lsp].setup {
    on_attach = nvlsp.on_attach,
    on_init = nvlsp.on_init,
    capabilities = nvlsp.capabilities,
  }
end

-- Null-ls setup for formatting
null_ls.setup({
  sources = {
    -- Add `tflint` with explicit path
    null_ls.builtins.diagnostics.tflint.with({
      command = "/opt/homebrew/bin/tflint", -- Ensure correct path
    }),
    null_ls.builtins.formatting.terraform_fmt, -- Formatting for Terraform
  },
})

-- Formatting fallback for terraform
vim.api.nvim_create_autocmd("BufWritePost", {
  pattern = "*.tf",
  callback = function()
    vim.lsp.buf.format({
      async = true,
      filter = function(client)
        return client.name == "null-ls" -- Ensure null-ls handles formatting
      end,
    })
  end,
})

