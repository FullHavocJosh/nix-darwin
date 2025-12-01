-- Setup notification logging to file
-- Log file: ~/.local/state/nvim/noice.log

local log_file = vim.fn.stdpath("state") .. "/noice.log"

-- Ensure directory exists
vim.fn.mkdir(vim.fn.stdpath("state"), "p")

-- Write init message
local file = io.open(log_file, "a")
if file then
  file:write(string.format("[%s] === Neovim session started ===\n", os.date("%Y-%m-%d %H:%M:%S")))
  file:close()
end

-- Hook into vim.notify to log all messages
local original_notify = vim.notify
vim.notify = function(msg, level, opts)
  -- Convert level number to string
  local level_names = {
    [vim.log.levels.TRACE] = "TRACE",
    [vim.log.levels.DEBUG] = "DEBUG",
    [vim.log.levels.INFO] = "INFO",
    [vim.log.levels.WARN] = "WARN",
    [vim.log.levels.ERROR] = "ERROR",
  }
  local level_str = level_names[level] or tostring(level or "INFO")

  -- Log to file
  local log_entry = string.format("[%s] [%s] %s\n", os.date("%Y-%m-%d %H:%M:%S"), level_str, tostring(msg))

  local f = io.open(log_file, "a")
  if f then
    f:write(log_entry)
    f:close()
  end

  -- Call original notify
  return original_notify(msg, level, opts)
end
