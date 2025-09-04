return {
	{
		"tomtom/tcomment_vim",
		config = function()
			vim.keymap.set("n", "<leader>/", ":TComment<CR>", { desc = "Toggle comment for current line" })
			vim.keymap.set("v", "<leader>/", ":TComment<CR>", { desc = "Toggle comment for selected lines" })
		end,
	},
}
