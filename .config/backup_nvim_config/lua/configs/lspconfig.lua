-- Load NVChad defaults
require("nvchad.configs.lspconfig").defaults()

local lspconfig = require "lspconfig"
local null_ls = require("null-ls")
local nvlsp = require "nvchad.configs.lspconfig"

-- LSP Servers list
local servers = {
    "html", -- HTML
    "cssls", -- CSS
    "terraformls", -- Terraform
    "yamlls", -- YAML
    "lua_ls", -- Lua
    "taplo", -- TOML
}

local augroup = vim.api.nvim_create_augroup("LspFormatting", {})

-- Define custom TFLint generator
local custom_tflint_generator = {
    name = "tflint",
    method = null_ls.methods.DIAGNOSTICS,
    filetypes = { "terraform" },
    generator = null_ls.generator({
        command = "/opt/homebrew/bin/tflint",
        args = { "--format", "json" },
        to_stdin = true,
        from_stderr = false,
        format = "json",
        on_output = function(params)
            local diagnostics = {}
            if params.output and type(params.output) == "table" then
                for _, diagnostic in ipairs(params.output) do
                    table.insert(diagnostics, {
                        row = diagnostic.range.start.line + 1,
                        col = diagnostic.range.start.character + 1,
                        message = diagnostic.message,
                        severity = diagnostic.severity,
                        source = "tflint",
                    })
                end
            end
            return diagnostics
        end,
    }),
}

-- Define custom Ansible-lint generator
local custom_ansible_lint_generator = {
    name = "ansible_lint",
    method = null_ls.methods.DIAGNOSTICS,
    filetypes = { "yaml", "yml", "yaml.ansible" },
    generator = null_ls.generator({
        command = "/opt/homebrew/bin/ansible-lint",
        args = { "--nocolor", "-" },
        to_stdin = true,
    }),
}

-- `on_attach` Function
local function on_attach(client, bufnr)
    print("Attached to " .. client.name) -- Debug
    if client.server_capabilities.documentFormattingProvider then
      print("Client supports formatting: " .. client.name)
      vim.api.nvim_clear_autocmds({ group = augroup, buffer = bufnr })
      vim.api.nvim_create_autocmd("BufWritePre", {
        group = augroup,
        buffer = bufnr,
        callback = function()
          vim.lsp.buf.format({
            bufnr = bufnr,
            filter = function(c)
              return c.name == "null-ls"
            end,
          })
        end,
      })
    end
end

-- Configure LSPs
for _, lsp in ipairs(servers) do
    lspconfig[lsp].setup {
        on_attach = on_attach,
        on_init = nvlsp.on_init, -- Retain the existing on_init from NVChad
        capabilities = nvlsp.capabilities,
    }
end

-- Null-ls setup for diagnostics and formatting
null_ls.setup({
    debug = true,
    on_attach = on_attach,
    sources = {
        -- Prettier for YAML and TOML formatting
        null_ls.builtins.formatting.prettier.with({
            filetypes = { "yaml", "yml", "toml", "yaml.ansible" },
        }),
        -- Stylua for Lua formatting
        null_ls.builtins.formatting.stylua.with({
            extra_args = { "--config-path", vim.fn.expand("~/.stylua.toml") },
        }),
        -- ShellCheck for Bash diagnostics (optional, but helpful)
        null_ls.builtins.diagnostics.shellcheck,
        -- Custom TFLint generator
        custom_tflint_generator,
        -- Custom Ansible-lint generator
        custom_ansible_lint_generator,
    },
})

-- Nix LSP setup
lspconfig.rnix.setup({
    filetypes = { "nix" },
})

-- Lua LSP setup
lspconfig.lua_ls.setup({
    settings = {
        Lua = {
            runtime = {
                version = "LuaJIT",
                path = vim.split(package.path, ";"),
            },
            diagnostics = {
                globals = { "vim" }, -- Recognize `vim` as a global
            },
            workspace = {
                library = vim.api.nvim_get_runtime_file("", true),
                checkThirdParty = false,
            },
            telemetry = {
                enable = false,
            },
        },
    },
})

-- YAML Language Server setup
lspconfig.yamlls.setup({
    cmd = { "yaml-language-server", "--stdio" },
    filetypes = { "yaml", "yml", "yaml.ansible" },
    settings = {
        yaml = {
            schemas = {
                ["https://json.schemastore.org/github-workflow.json"] = ".github/workflows/*",
                ["https://raw.githubusercontent.com/ansible-community/schemas/main/f/ansible-tasks.json"] = "tasks/*.yml",
            },
            validate = true,
            format = {
                enable = true,
            },
        },
    },
})

lspconfig.lua_ls.setup({
    settings = {
        Lua = {
            runtime = {
                version = "LuaJIT", -- Use LuaJIT runtime for Neovim
                path = vim.split(package.path, ";"),
            },
            diagnostics = {
                globals = { "vim" }, -- Recognize `vim` as a global
            },
            workspace = {
                library = vim.api.nvim_get_runtime_file("", true), -- Include Neovim runtime files
                checkThirdParty = false, -- Disable third-party module checks
            },
            telemetry = {
                enable = false, -- Disable telemetry for privacy
            },
        },
    },
})

-- Null-ls setup for diagnostics and formatting
print("Setting up null-ls...") -- Debug
null_ls.setup({
    on_attach = on_attach,
    sources = {
        -- Built-in formatting sources
        null_ls.builtins.formatting.prettier.with({
            filetypes = { "yaml", "yml", "toml", "yaml.ansible" },
        }),
        null_ls.builtins.formatting.stylua.with({
            extra_args = { "--config-path", vim.fn.expand("~/.stylua.toml") },
        }),
        null_ls.builtins.diagnostics.shellcheck,
        -- Custom tflint generator
        custom_tflint_generator,
        -- Custom ansible-lint generator
        custom_ansible_lint_generator,
    },
})
print("null-ls setup complete!") -- Debug

vim.filetype.add({
    extension = {
        yml = "yaml.ansible",
    },
})

-- Formatting and linting for .tf files
vim.api.nvim_create_autocmd("BufWritePost", {
    pattern = "*.tf",
    callback = function()
        vim.lsp.buf.format({
            async = true,
            filter = function(client)
                return client.name == "null-ls"
            end,
        })
    end,
})

-- Formatting and linting for .yml, .yaml, and .toml files
vim.api.nvim_create_autocmd("BufWritePre", {
    pattern = { "*.yml", "*.yaml", "*.toml", "yaml.ansible" },
    callback = function()
        vim.lsp.buf.format({
            async = false,
            filter = function(client)
                return client.name == "null-ls"
            end,
        })
    end,
})

-- Nix LSP setup
lspconfig.rnix.setup({
    filetypes = { "nix" },
})

-- YAML Language Server setup
lspconfig.yamlls.setup({
    cmd = { "yaml-language-server", "--stdio" },
    filetypes = { "yaml", "yml", "yaml.ansible" },
    settings = {
        yaml = {
            schemas = {
                ["https://json.schemastore.org/github-workflow.json"] = ".github/workflows/*",
                ["https://raw.githubusercontent.com/ansible-community/schemas/main/f/ansible-tasks.json"] = "tasks/*.yml",
            },
            validate = true,
            format = {
                enable = true,
            },
        },
    },
})

