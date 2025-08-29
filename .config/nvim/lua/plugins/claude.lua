return {
	{
		"pasky/claude.vim",
		config = function()
			-- Claude configuration
			-- You'll need to set your Claude API key in environment or via command
			-- export ANTHROPIC_API_KEY="your-api-key-here"
			
			-- Basic keymaps for Claude functionality
			vim.keymap.set("n", "<leader>cc", ":ClaudeChat<CR>", { desc = "Claude Chat" })
			vim.keymap.set("v", "<leader>ce", ":ClaudeExplain<CR>", { desc = "Claude Explain Selection" })
			vim.keymap.set("v", "<leader>cr", ":ClaudeRewrite<CR>", { desc = "Claude Rewrite Selection" })
			vim.keymap.set("n", "<leader>cf", ":ClaudeFile<CR>", { desc = "Claude Analyze File" })
		end,
	},
}