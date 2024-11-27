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

        -- Format on save
        vim.api.nvim_create_autocmd("BufWritePre", {
            callback = function()
                vim.cmd("FormatWrite")
            end,
        })
    end,
}
