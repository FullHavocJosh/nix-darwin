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
    -- Force treesitter to attach if it's loaded
    vim.defer_fn(function()
      if vim.fn.exists(":TSBufEnable") > 0 then
        vim.cmd("TSBufEnable highlight")
      end
    end, 100)
  end,
})

-- Additional autocmd to re-enable highlighting after entering a buffer
vim.api.nvim_create_autocmd("BufEnter", {
  pattern = {"*.tf", "*.tfvars"},
  callback = function()
    if vim.bo.filetype ~= "terraform" then
      vim.bo.filetype = "terraform"
      if vim.fn.exists(":TSBufEnable") > 0 then
        vim.cmd("TSBufEnable highlight")
      end
    end
  end,
})