return {
    "mhartington/formatter.nvim",
    config = function()
        require("formatter").setup({
            logging = false,
            filetype = {
                bash = {
                    function()
                        return {
                            exe = "shfmt",
                            args = { "-i", "2" },
                            stdin = true,
                        }
                    end,
                },
                yaml = {
                    function()
                        return {
                            exe = "prettier",
                            args = { "--stdin-filepath", vim.fn.expand("%:p") },
                            stdin = true,
                        }
                    end,
                },
                json = {
                    function()
                        return {
                            exe = "prettier",
                            args = { "--stdin-filepath", vim.fn.expand("%:p") },
                            stdin = true,
                        }
                    end,
                },
                lua = {
                    function()
                        return {
                            exe = "stylua",
                            args = { "-" },
                            stdin = true,
                        }
                    end,
                },
                python = {
                    function()
                        return {
                            exe = "black",
                            args = { "-" },
                            stdin = true,
                        }
                    end,
                },
            },
        })

        -- Format on save (exclude terraform files - handled by LSP)
        vim.api.nvim_create_autocmd("BufWritePre", {
            callback = function()
                local filetype = vim.bo.filetype
                if filetype ~= "terraform" then
                    vim.cmd("FormatWrite")
                end
            end,
        })
    end,
}
