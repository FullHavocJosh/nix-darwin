...m/lazy/telescope.nvim/lua/telescope/_extensions/init.lua:10: 'fzf' extension doesn't exist or isn't installed: ...hare/nvim/lazy/telescope-fzf-native.nvim/lua/fzf_lib.lu
a:11: /home/havoc/.local/share/nvim/lazy/telescope-fzf-native.nvim/lua/../build/libfzf.so: cannot open shared object file: No such file or directory

# stacktrace:
  - /telescope.nvim/lua/telescope/_extensions/init.lua:10 _in_ **load_extension**
  - /telescope.nvim/lua/telescope/_extensions/init.lua:62 _in_ **load_extension**
  - ~/.config/nvim/lua/plugins/telescope.lua:22 _in_ **config**
  - ~/.config/nvim/lua/config/lazy.lua:25
  - .config/nvim/init.lua:4
Press ENTER or type command to continue
prettier: installing
Press ENTER or type command to continue
eslint_d: installing
Press ENTER or type command to continue
Press ENTER or type command to continue
Press ENTER or type command to continue
Error executing vim.schedule lua callback: vim/_editor.lua:0: nvim_exec2(), line 1: Vim:prettier: failed to install
stack traceback:
        [C]: in function 'nvim_exec2'
        vim/_editor.lua: in function 'cmd'
        /home/havoc/.config/nvim/lua/plugins/nvim-tree.lua:66: in function ''
        vim/_editor.lua: in function ''
        vim/_editor.lua: in function <vim/_editor.lua:0>
Press ENTER or type command to continue
