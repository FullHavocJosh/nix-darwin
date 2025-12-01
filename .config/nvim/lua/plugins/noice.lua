-- Log all Noice messages to file: ~/.local/state/nvim/noice.log
-- View messages with: :Noice or tail -f ~/.local/state/nvim/noice.log
return {
  "folke/noice.nvim",
  opts = function(_, opts)
    -- Suppress UI notifications during startup
    opts.routes = opts.routes or {}

    table.insert(opts.routes, {
      filter = {
        event = "notify",
        cond = function()
          return vim.fn.has("vim_starting") == 1
        end,
      },
      opts = { skip = true },
    })

    -- Disable LSP progress in UI
    opts.lsp = opts.lsp or {}
    opts.lsp.progress = { enabled = false }

    return opts
  end,
}
