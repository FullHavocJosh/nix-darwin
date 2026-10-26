-- LazyVim's which-key spec makes <leader>w a "windows" group (a proxy for ctrl+w). <leader>w closes the buffer here
-- (config/keymaps.lua), so drop that group; ctrl+w itself still shows the window commands.
local function drop_leader_w(spec)
  for i = #spec, 1, -1 do
    local item = spec[i]
    if type(item) == "table" then
      if item[1] == "<leader>w" then
        table.remove(spec, i)
      else
        drop_leader_w(item)
      end
    end
  end
end

return {
  "folke/which-key.nvim",
  opts = function(_, opts)
    drop_leader_w(opts.spec or {})
  end,
}
