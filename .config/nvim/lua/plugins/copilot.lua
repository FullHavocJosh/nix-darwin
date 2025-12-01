return {
  "github/copilot.vim",
  event = "InsertEnter",
  config = function()
    -- Disable default Tab mapping to avoid conflicts with blink.cmp
    vim.g.copilot_no_tab_map = true
    vim.g.copilot_assume_mapped = true
    vim.g.copilot_tab_fallback = ""

    -- Use Alt+] to accept Copilot suggestion (avoids conflict with Tab completion)
    vim.keymap.set("i", "<M-]>", 'copilot#Accept("")', {
      expr = true,
      replace_keycodes = false,
      desc = "Accept Copilot suggestion",
    })

    -- Navigate between Copilot suggestions
    vim.keymap.set("i", "<M-[>", "copilot#Next()", {
      expr = true,
      replace_keycodes = false,
      desc = "Next Copilot suggestion",
    })

    vim.keymap.set("i", "<M-{>", "copilot#Previous()", {
      expr = true,
      replace_keycodes = false,
      desc = "Previous Copilot suggestion",
    })

    -- Alternative: Use Ctrl+J to accept (more accessible than Alt)
    vim.keymap.set("i", "<C-J>", 'copilot#Accept("")', {
      expr = true,
      replace_keycodes = false,
      desc = "Accept Copilot suggestion (Ctrl-J)",
    })
  end,
}
