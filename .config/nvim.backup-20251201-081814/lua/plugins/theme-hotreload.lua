return {
	{
		name = "theme-hotreload",
		dir = vim.fn.stdpath("config"),
		lazy = false,
		priority = 900,
		config = function()
			local transparency_file = vim.fn.stdpath("config") .. "/plugin/after/transparency.lua"

			vim.api.nvim_create_autocmd("User", {
				pattern = "LazyReload",
				callback = function()
					-- Clear all highlight groups before applying new theme
					vim.cmd("highlight clear")
					if vim.fn.exists("syntax_on") then
						vim.cmd("syntax reset")
					end

					-- Reset background to default so colorscheme can set it properly
					vim.o.background = "dark"

					vim.schedule(function()
						-- Reapply the current colorscheme
						local current_colorscheme = vim.g.colors_name or "catppuccin"
						
						vim.defer_fn(function()
							-- Apply the colorscheme
							pcall(vim.cmd.colorscheme, current_colorscheme)

							-- Force redraw to update all UI elements
							vim.cmd("redraw!")

							-- Reload transparency settings
							if vim.fn.filereadable(transparency_file) == 1 then
								vim.defer_fn(function()
									vim.cmd.source(transparency_file)

									-- Trigger UI updates for various plugins
									vim.api.nvim_exec_autocmds("ColorScheme", { modeline = false })

									-- Final redraw
									vim.cmd("redraw!")
								end, 5)
							end
						end, 5)
					end)
				end,
			})
		end,
	},
}
