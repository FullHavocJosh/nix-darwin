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

-- Set commentstring for Terraform files
vim.api.nvim_create_autocmd({"FileType"}, {
  pattern = "terraform",
  callback = function()
    vim.bo.commentstring = "# %s"
  end,
})