-- Suppress non-critical messages during the first 2 seconds of startup
-- This prevents noise from plugins loading in the background

local startup_time = vim.loop.hrtime()
local suppress_duration = 2 * 1e9 -- 2 seconds in nanoseconds
local original_notify = vim.notify

vim.notify = function(msg, level, opts)
  local current_time = vim.loop.hrtime()
  local elapsed = current_time - startup_time

  -- During startup window, only show ERROR messages
  if elapsed < suppress_duration then
    if level == vim.log.levels.ERROR then
      original_notify(msg, level, opts)
    end
    return
  end

  -- After startup window, show all messages normally
  original_notify(msg, level, opts)
end

-- Restore original notify function after 2 seconds
vim.defer_fn(function()
  vim.notify = original_notify
end, 2000)
