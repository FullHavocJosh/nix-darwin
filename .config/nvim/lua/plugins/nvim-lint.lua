return {
  "mfussenegger/nvim-lint",
  config = function()
    local lint = require("lint")

    lint.linters_by_ft = {
      -- Configuration files
      yaml = { "yamllint" },
      yml = { "yamllint" },
      json = { "jsonlint" },
      toml = { "taplo" },

      -- Shell scripting
      sh = { "shellcheck" },
      bash = { "shellcheck" },
      zsh = { "shellcheck" },

      -- Programming languages
      lua = { "luacheck" },
      python = { "ruff", "mypy" },
      javascript = { "eslint_d" },
      typescript = { "eslint_d" },
      javascriptreact = { "eslint_d" },
      typescriptreact = { "eslint_d" },
      go = { "golangcilint" },
      ruby = { "rubocop" },

      -- Infrastructure as Code
      terraform = { "tflint", "tfsec" },
      tf = { "tflint", "tfsec" },
      hcl = { "tflint" },

      -- Ansible
      ansible = { "ansible_lint" },
      ["yaml.ansible"] = { "ansible_lint", "yamllint" },

      -- Docker
      dockerfile = { "hadolint" },

      -- Markup
      markdown = { "markdownlint" },

      -- SQL
      sql = { "sqlfluff" },

      -- PowerShell
      ps1 = { "powershell_analyzer" },
      psm1 = { "powershell_analyzer" },
    }

    -- Custom linter configurations
    -- Ansible-lint configuration
    lint.linters.ansible_lint = {
      cmd = "ansible-lint",
      stdin = false,
      args = { "--nocolor", "--parseable-severity" },
      stream = "stdout",
      ignore_exitcode = true,
      parser = require("lint.parser").from_pattern(
        "([^:]+):(%d+):?(%d*): %[([%w-]+)%] ([^%[]+)%[([%w-]+)%]",
        { "file", "lnum", "col", "severity", "message", "code" },
        {
          ["VERY_HIGH"] = vim.diagnostic.severity.ERROR,
          ["HIGH"] = vim.diagnostic.severity.ERROR,
          ["MEDIUM"] = vim.diagnostic.severity.WARN,
          ["LOW"] = vim.diagnostic.severity.INFO,
          ["VERY_LOW"] = vim.diagnostic.severity.HINT,
        }
      ),
    }

    -- TFSec configuration for Terraform security scanning
    lint.linters.tfsec = {
      cmd = "tfsec",
      stdin = false,
      args = { "--format", "json", "--no-color" },
      stream = "stdout",
      ignore_exitcode = true,
      parser = function(output, bufnr)
        local diagnostics = {}
        local ok, decoded = pcall(vim.json.decode, output)
        if not ok or not decoded or not decoded.results then
          return diagnostics
        end

        for _, result in ipairs(decoded.results) do
          if result.location and result.location.start_line then
            table.insert(diagnostics, {
              lnum = result.location.start_line - 1,
              end_lnum = result.location.end_line and (result.location.end_line - 1) or nil,
              col = 0,
              message = string.format("[%s] %s", result.rule_id or "unknown", result.description or "Security issue"),
              severity = result.severity == "CRITICAL" and vim.diagnostic.severity.ERROR
                or result.severity == "HIGH" and vim.diagnostic.severity.ERROR
                or result.severity == "MEDIUM" and vim.diagnostic.severity.WARN
                or vim.diagnostic.severity.INFO,
              source = "tfsec",
            })
          end
        end
        return diagnostics
      end,
    }

    -- PowerShell Script Analyzer (requires pwsh and PSScriptAnalyzer module)
    lint.linters.powershell_analyzer = {
      cmd = "pwsh",
      stdin = false,
      args = {
        "-NoProfile",
        "-Command",
        "Invoke-ScriptAnalyzer -Path $FILENAME -EnableExit",
      },
      stream = "stdout",
      ignore_exitcode = true,
      parser = require("lint.parser").from_pattern(
        "(%d+):(%d+): (%w+): (.+)",
        { "lnum", "col", "severity", "message" },
        {
          ["Error"] = vim.diagnostic.severity.ERROR,
          ["Warning"] = vim.diagnostic.severity.WARN,
          ["Information"] = vim.diagnostic.severity.INFO,
        }
      ),
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
