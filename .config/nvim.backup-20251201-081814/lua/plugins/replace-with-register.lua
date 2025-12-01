return {
    {
        "vim-scripts/ReplaceWithRegister", -- Plugin repository
    },
}
--USAGE
--[count]["x]gr{motion}   Replace {motion} text with the contents of register x.
--                        Especially when using the unnamed register, this is
--                        quicker than "_d{motion}P or "_c{motion}<C-R>"
--[count]["x]grr          Replace [count] lines with the contents of register x.
--                        To replace from the cursor position to the end of the
--                        line use ["x]gr$
--{Visual}["x]gr          Replace the selection with the contents of register x.
