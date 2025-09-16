-- Filetype detection and configuration
vim.filetype.add({
  extension = {
    tf = "terraform",
    tfvars = "terraform",
    hcl = "hcl",
  },
  filename = {
    [".terraformrc"] = "hcl",
    ["terraform.rc"] = "hcl",
  },
  pattern = {
    [".*%.tf%.json$"] = "json",
  },
})

-- Ensure Terraform files use proper syntax highlighting
vim.api.nvim_create_autocmd({"BufRead", "BufNewFile"}, {
  pattern = {"*.tf", "*.tfvars", "*.hcl"},
  callback = function()
    vim.bo.filetype = "terraform"
    vim.bo.commentstring = "# %s"
  end,
})