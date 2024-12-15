module.exports = {
    config: {
        // Fonts
        fontSize: 14,
        fontFamily: 'JetBrainsMono Nerd Font, monospace',

        css: `
            .xterm {
                font-family: 'JetBrainsMono Nerd Font', monospace !important;
            }
        `,

        env: {
            TERM: 'xterm-256color'
        },
        webGLRenderer: false,

        // Catppuccin Mocha theme
        catppuccinTheme: 'Mocha',

        // Padding
        padding: '5px',

        // Cursor settings
        cursorBlink: true,
        cursorShape: 'BLOCK',

        // Scrolling
        scrollback: 100000,

        // Shell configuration
        shell: '/bin/zsh',

        // Bell configuration
        bell: false,

        // Disable keymaps
        keymaps: {},
    },

    // Plugins (can install plugins for themes or other features if needed)
    plugins: ["hyper-search", "hypercwd", "hypurr", "hyper-font-ligatures", "hyper-quit"],

    // Local plugins
    localPlugins: [],

    // Un-comment below if you want to use Hyper in debug mode
    // development: true
};
