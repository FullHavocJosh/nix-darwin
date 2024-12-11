module.exports = {
    config: {
        // Fonts
        fontSize: 14,
        fontFamily: 'JetBrainsMono Nerd Font, monospace',

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

        // Keymaps (similar to Kitty shortcuts)
        keymaps: {
            'window:devtools': 'cmd+alt+o', // Example Hyper default keymaps
            'editor:copy': 'cmd+c',
            'editor:paste': 'cmd+v',
            'search:find': 'cmd+f',
        },
    },

    // Plugins (can install plugins for themes or other features if needed)
    plugins: ["hyper-search", "hypercwd", "hypurr"],

    // Local plugins
    localPlugins: [],

    // Un-comment below if you want to use Hyper in debug mode
    // development: true
};
