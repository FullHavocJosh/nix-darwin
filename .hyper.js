// Hyper configuration
// Configured to match ghostty settings

module.exports = {
  config: {
    // Font configuration
    fontSize: 14,
    fontFamily: '"JetBrains Mono", monospace',
    fontWeight: "normal",
    fontWeightBold: "bold",

    // Cursor
    cursorColor: "rgba(248, 248, 242, 0.8)",
    cursorAccentColor: "#000",
    cursorShape: "BLOCK",
    cursorBlink: false,

    // Colors - Catppuccin Mocha theme
    foregroundColor: "#cdd6f4",
    backgroundColor: "#1e1e2e", // Solid background, no transparency
    selectionColor: "rgba(88, 91, 112, 0.5)",
    borderColor: "#11111b",

    colors: {
      black: "#45475a",
      red: "#f38ba8",
      green: "#a6e3a1",
      yellow: "#f9e2af",
      blue: "#89b4fa",
      magenta: "#f5c2e7",
      cyan: "#94e2d5",
      white: "#bac2de",
      lightBlack: "#585b70",
      lightRed: "#f38ba8",
      lightGreen: "#a6e3a1",
      lightYellow: "#f9e2af",
      lightBlue: "#89b4fa",
      lightMagenta: "#f5c2e7",
      lightCyan: "#94e2d5",
      lightWhite: "#a6adc8",
    },

    // Shell
    shell: "/bin/zsh",
    shellArgs: [],

    // Environment
    env: {
      TERM: "xterm-256color",
    },

    // Bell
    bell: false,

    // Copy on select
    copyOnSelect: true,

    // Default SSH/Telnet connection dropdown
    defaultSSHApp: true,

    // Quick edit
    quickEdit: false,

    // Padding
    padding: "0px",

    // Window settings
    windowSize: [800, 600], // Initial size before maximizing

    // Scrollback
    scrollback: 100000,

    // Background opacity (Note: Hyper's background opacity is set in backgroundColor rgba)
    // Background blur is not natively supported in Hyper without plugins

    // URL handling
    webGLRenderer: true,
    webLinksActivationKey: "meta",

    // Disable ligatures (can be enabled if desired)
    disableLigatures: false,

    // Dynamic title
    showHamburgerMenu: false,
    showWindowControls: false,
  },

  // Plugins configuration
  plugins: [
    "hyper-pane", // For better pane management
  ],

  // Local plugins
  localPlugins: [],

  // Keymaps
  keymaps: {
    // Add custom keybindings here if needed
  },
};
