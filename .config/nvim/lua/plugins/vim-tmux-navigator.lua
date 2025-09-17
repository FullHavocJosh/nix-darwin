return {
    "christoomey/vim-tmux-navigator",
    lazy = false,
    keys = {
        { "<c-h>", "<cmd>TmuxNavigateLeft<cr>" },
        { "<c-j>", "<cmd>TmuxNavigateDown<cr>" },
        { "<c-k>", "<cmd>TmuxNavigateUp<cr>" },
        { "<c-l>", "<cmd>TmuxNavigateRight<cr>" },
        { "<c-\\>", "<cmd>TmuxNavigatePrevious<cr>" },
    },
    init = function()
        vim.g.tmux_navigator_no_mappings = 1
        vim.g.tmux_navigator_disable_when_zoomed = 1
    end,
}
