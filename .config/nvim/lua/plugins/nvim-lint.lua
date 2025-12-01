return {
  "mfussenegger/nvim-lint",
  config = function()
    local lint = require("lint")

    lint.linters_by_ft = {
      yaml = { "yamllint" },
      ansible = { "ansible-lint" },
    }

    -- Auto-lint on save and text change (only for configured filetypes)
    vim.api.nvim_create_autocmd({ "BufWritePost", "BufReadPost", "InsertLeave" }, {
      callback = function()
        local filetype = vim.bo.filetype
        if lint.linters_by_ft[filetype] then
          lint.try_lint()
        end
      end,
    })
  end,
}
