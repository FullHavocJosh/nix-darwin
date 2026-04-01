return {
  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "saghen/blink.cmp",
      "mason-org/mason-lspconfig.nvim",
      "glepnir/lspsaga.nvim",
    },
    config = function()
      local capabilities = require("blink.cmp").get_lsp_capabilities()
      local keymap = vim.keymap

      local signs = { Error = " ", Warn = " ", Hint = "ﴞ ", Info = " " }
      for type, icon in pairs(signs) do
        local hl = "DiagnosticSign" .. type
        vim.fn.sign_define(hl, { text = icon, texthl = hl, numhl = "" })
      end

      local augroup = vim.api.nvim_create_augroup("LspFormatting", {})

      local on_attach = function(client, bufnr)
        local opts = { noremap = true, silent = true, buffer = bufnr }
        if client.name == "ts_ls" or client.name == "tsserver" then
          keymap.set("n", "<leader>rf", ":TypescriptRenameFile<CR>", opts)
          keymap.set("n", "<leader>oi", ":TypescriptOrganizeImports<CR>", opts)
          keymap.set("n", "<leader>ru", ":TypescriptRemoveUnused<CR>", opts)
        end
      end

      local servers = {
        bashls = {},
        ansiblels = {
          settings = {
            ansible = {
              ansible = { path = "ansible" },
              ansibleLint = { enabled = true, path = "ansible-lint" },
              python = { interpreterPath = "python3" },
            },
          },
        },
        dockerls = {},
        docker_compose_language_service = {},
        lua_ls = {
          settings = {
            Lua = {
              format = { enable = true },
              diagnostics = { globals = { "vim" } },
            },
          },
        },
        pylsp = {
          settings = {
            pylsp = {
              plugins = {
                pycodestyle = { enabled = false },
                mccabe = { enabled = false },
                pyflakes = { enabled = false },
                ruff = { enabled = true },
                autopep8 = { enabled = false },
                yapf = { enabled = false },
                black = { enabled = true },
              },
            },
          },
        },
        ts_ls = {},
        yamlls = {
          settings = {
            yaml = {
              schemas = {
                kubernetes = "/*.k8s.{yaml,yml}",
                ["https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.28.0/all.json"] = "/*k8s*.{yaml,yml}",
                ["https://raw.githubusercontent.com/ansible/ansible-lint/main/src/ansiblelint/schemas/ansible.json"] = "/ansible/**/*.{yaml,yml}",
                ["https://raw.githubusercontent.com/ansible/ansible-lint/main/src/ansiblelint/schemas/playbook.json"] = "/*playbook*.{yaml,yml}",
                ["https://raw.githubusercontent.com/aws/aws-cloudformation-templates/main/aws-cfn-template-2010-09-09.json"] = "/*cloudformation*.{yaml,yml}",
                ["https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json"] = "/docker-compose*.{yaml,yml}",
                ["https://json.schemastore.org/github-workflow.json"] = "/.github/workflows/*.{yaml,yml}",
                ["https://json.schemastore.org/gitlab-ci.json"] = "/.gitlab-ci.{yaml,yml}",
              },
              validate = true,
              format = { enable = true },
              hover = true,
              completion = true,
            },
          },
        },
        terraformls = {
          settings = { terraform = { timeout = "30s" } },
        },
        powershell_es = {
          bundle_path = vim.fn.stdpath("data") .. "/mason/packages/powershell-editor-services",
        },
        solargraph = {},
        lemminx = {},
        taplo = {},
        gopls = {
          settings = {
            gopls = {
              analyses = { unusedparams = true, shadow = true },
              staticcheck = true,
              gofumpt = true,
            },
          },
        },
        jsonls = {
          settings = {
            json = {
              schemas = require("schemastore").json.schemas(),
              validate = { enable = true },
            },
          },
        },
        marksman = {},
      }

      local lspconfig = require("lspconfig")
      for server, config in pairs(servers) do
        local server_config = vim.tbl_deep_extend("force", {
          capabilities = capabilities,
          on_attach = on_attach,
        }, config)
        lspconfig[server].setup(server_config)
      end
    end,
  },
}
