# Omarchy Configuration

This repository contains customized Omarchy configuration following the standard overlay pattern where base configs source custom overlays.

## Configuration Structure

Omarchy configuration files are organized with a clean separation between defaults and customizations:

```
~/.config/hypr/
├── hyprland.conf          # Main config (sources everything)
├── bindings.conf          # Sources custom.bindings.conf
├── monitors.conf          # Sources custom.monitors.conf
├── input.conf             # Sources custom.input.conf
├── looknfeel.conf         # Sources custom.looknfeel.conf
├── autostart.conf         # Sources custom.autostart.conf
├── custom.bindings.conf   # Personal keybindings
├── custom.monitors.conf   # Personal monitor setup
├── custom.input.conf      # Personal input settings
├── custom.looknfeel.conf  # Personal appearance tweaks
├── custom.autostart.conf  # Personal autostart apps
├── custom.windows.conf    # Personal window rules
├── hyprpaper.conf         # Wallpaper config (standalone)
└── hypridle.conf          # Idle/lock config (standalone)
```

## Customized Keybindings

### Core Applications

| Keybind             | Application       | Command                            | Notes                                                       |
| ------------------- | ----------------- | ---------------------------------- | ----------------------------------------------------------- |
| `SUPER+RETURN`      | Terminal          | `xdg-terminal-exec`                | Uses system default terminal with current working directory |
| `SUPER+SHIFT+F`     | File Manager      | Nautilus                           | Opens in new window                                         |
| `SUPER+SHIFT+B`     | Browser           | `omarchy-launch-browser`           | Uses system default (currently Zen Browser)                 |
| `SUPER+SHIFT+ALT+B` | Browser (Private) | `omarchy-launch-browser --private` | Auto-detects incognito/private flag                         |
| `SUPER+SHIFT+M`     | Music             | Cider                              | Launch or focus if running                                  |
| `SUPER+SHIFT+N`     | Editor            | `omarchy-launch-editor`            | Uses `$EDITOR` env var (nvim)                               |
| `SUPER+SHIFT+T`     | Activity Monitor  | btop                               | Terminal UI                                                 |
| `SUPER+SHIFT+D`     | Discord           | Discord                            | Launch or focus if running                                  |
| `SUPER+SHIFT+O`     | Obsidian          | Obsidian                           | Note-taking app with Wayland IME                            |
| `SUPER+SHIFT+/`     | Passwords         | Proton Pass                        | Password manager                                            |

### AI & Development

| Keybind             | Application | Command            | Notes                                                              |
| ------------------- | ----------- | ------------------ | ------------------------------------------------------------------ |
| `SUPER+SHIFT+A`     | AI Dev      | `aidev` function   | Interactive menu: OpenCode (Copilot) or Crush (Bedrock/OpenRouter) |
| `SUPER+SHIFT+ALT+A` | OpenRouter  | openrouter.ai/chat | AI chat interface as PWA                                           |

### Productivity Web Apps (PWA Mode)

| Keybind         | Application | URL            | Notes              |
| --------------- | ----------- | -------------- | ------------------ |
| `SUPER+SHIFT+E` | Email       | mail.proton.me | Proton Mail as PWA |
| `SUPER+SHIFT+Y` | YouTube     | youtube.com    | YouTube as PWA     |

## Default Omarchy Keybindings

These are the standard Omarchy keybindings that remain unchanged:

### Window Management

- `SUPER+W` - Close window
- `CTRL+ALT+DELETE` - Close all windows
- `SUPER+J` - Toggle split
- `SUPER+T` - Toggle floating/tiling
- `SUPER+F` - Fullscreen
- `SUPER+CTRL+F` - Tiled fullscreen
- `SUPER+Arrow keys` - Move focus

### Workspaces

- `SUPER+1-0` - Switch to workspace 1-10
- `SUPER+SHIFT+1-0` - Move window to workspace
- `SUPER+TAB` - Next workspace
- `SUPER+SHIFT+TAB` - Previous workspace
- `ALT+TAB` - Cycle windows

### Scratchpad

- `SUPER+S` - Toggle scratchpad
- `SUPER+ALT+S` - Move window to scratchpad

### Menus & Launchers

- `SUPER+SPACE` - App launcher (Walker)
- `SUPER+CTRL+E` - Emoji picker
- `SUPER+ALT+SPACE` - Omarchy menu
- `SUPER+ESCAPE` - System menu
- `SUPER+K` - Show keybindings

### Aesthetics

- `SUPER+SHIFT+SPACE` - Toggle top bar (Waybar)
- `SUPER+CTRL+SPACE` - Next background in theme
- `SUPER+SHIFT+CTRL+SPACE` - Theme menu
- `SUPER+BACKSPACE` - Toggle window transparency
- `SUPER+SHIFT+BACKSPACE` - Toggle workspace gaps

### Notifications

- `SUPER+,` - Dismiss last notification
- `SUPER+SHIFT+,` - Dismiss all notifications
- `SUPER+CTRL+,` - Toggle DND mode

### Utilities

- `SUPER+CTRL+I` - Toggle auto-lock on idle
- `SUPER+CTRL+N` - Toggle nightlight
- `SUPER+CTRL+T` - Show time
- `SUPER+CTRL+B` - Show battery level

### Captures

- `PRINT` - Screenshot with editing
- `SHIFT+PRINT` - Screenshot to clipboard
- `ALT+PRINT` - Screen recording menu
- `SUPER+PRINT` - Color picker

### Media Controls

- `XF86Audio*` keys - Volume/brightness/playback
- `ALT+XF86Audio*` - Precise 1% adjustments

### Clipboard

- `SUPER+C` - Universal copy
- `SUPER+V` - Universal paste
- `SUPER+X` - Universal cut
- `SUPER+CTRL+V` - Clipboard manager

## ZSH Configuration

### Shell Keybindings (.zshrc_os_linux_omarchy_keybindings)

- **Vi mode** - `bindkey -v`
- **Up/Down arrows** - History search matching typed text
- **Ctrl+R** - Reverse search

### Aliases (.zshrc_os_linux_omarchy_aliases)

**File system:**

```bash
ls      # eza -lh --group-directories-first --icons=auto
lsa     # ls -a
lt      # eza --tree --level=2
lta     # lt -a
ff      # fzf with bat preview
cd      # zd (zoxide wrapper)
..      # cd ..
...     # cd ../..
....    # cd ../../..
```

**Tools:**

```bash
d       # docker
r       # rails
n       # nvim (opens current dir if no args)
g       # git
gcm     # git commit -m
gcam    # git commit -a -m
gcad    # git commit -a --amend
```

**System:**

```bash
open    # xdg-open (background process)
```

### Custom Functions (.zshrc_functions)

**aidev** - AI Coding Assistant Selector

- Interactive menu to choose between:
  - **OpenCode** (GitHub Copilot + AWS Bedrock)
  - **Crush** (AWS Bedrock + OpenRouter)
- Handles authentication checks
- Auto-detects available providers

**asc** - AWS Configure

```bash
asc <profile>   # Export AWS credentials for profile
asc clear       # Unset all AWS_* env vars
```

## Managing Omarchy Themes with Git Submodules

This repository manages Omarchy themes as git submodules, deployed via stow.

### Quick Start

#### Option 1: Add Curated Themes (36 selected themes)

```bash
cd ~/nix-darwin/scripts
./linux-add-omarchy-themes-as-submodules.sh
```

This adds a curated selection of 36 themes that you've chosen.

#### Option 2: Add Individual Themes

1. Browse available themes in `omarchy-theme-urls.txt`
2. Add individual themes:

```bash
cd ~/nix-darwin

# Example: Add catppuccin-dark theme
THEME_URL="https://github.com/Luquatic/omarchy-catppuccin-dark"
THEME_NAME=$(basename "$THEME_URL" .git | sed -E 's/^omarchy-//; s/-theme$//')
git submodule add "$THEME_URL" ".config/omarchy/themes/$THEME_NAME"

# Repeat for other themes you want
```

3. Commit the changes:

```bash
git add .gitmodules .config/omarchy/
git commit -m "Add Omarchy themes as submodules"
```

### Deploy with Stow

After adding themes, deploy them to your home directory:

```bash
cd ~
stow --target=$HOME nix-darwin/.config
# or if you stow from the repo directory:
cd ~/nix-darwin
stow --target=$HOME .config
```

This creates symlinks:

- `~/.config/omarchy/themes/catppuccin-dark` → `~/nix-darwin/.config/omarchy/themes/catppuccin-dark`

### Using Themes

Switch themes using:

```bash
omarchy-theme-set <theme-name>
```

Or via the Omarchy menu: `Super+Alt+Space` → Change > Style > Theme

You can also use the keyboard shortcut: `SUPER+SHIFT+CTRL+SPACE` for the theme menu.

### Updating Themes

Update all theme submodules:

```bash
cd ~/nix-darwin
git submodule update --remote --merge
git commit -am "Update Omarchy themes"
```

### Cloning on a New Machine

After cloning this repo elsewhere:

```bash
git clone <your-repo-url> ~/nix-darwin
cd ~/nix-darwin
git submodule update --init --recursive
stow --target=$HOME .config
```

### Removing a Theme

```bash
cd ~/nix-darwin
git submodule deinit .config/omarchy/themes/<theme-name>
git rm .config/omarchy/themes/<theme-name>
git commit -m "Remove <theme-name> theme"
```

### Curated Theme List (36 themes)

The script adds these themes:

- aetheria, arc-blueberry, archwave, aura, ayaka, azure-glow
- blackturq, bluedotrb, blueridge-dark, catppuccin-dark
- citrus-cynapse, demon, dotrb, drac, dracula, eldritch
- felix, fireside, flexoki-dark, futurism, hakker-green
- mars, midnight, monokai, neovoid, nes, pandora, pulsar
- purple-moon, sunset-drive, temerald, tokyoled, torrentz-hydra
- waveform-dark, vhs80, void

### Theme Structure

```
~/nix-darwin/
├── .config/
│   └── omarchy/
│       └── themes/
│           ├── catppuccin-dark/     (submodule)
│           ├── dracula/              (submodule)
│           ├── tokyo-night/          (submodule)
│           └── ... (33 more)
└── .gitmodules
```

## Applications

### GUI Applications (Flatpak)

**Currently Installed:**

- Plexamp - Music player
- Sublime Text 3 - Text editor
- Ungoogled Chromium - Browser
- LibreWolf - Browser
- Krita - Digital painting
- VLC - Media player

**To be installed:**

- **Cider** - Apple Music client (keybind: SUPER+SHIFT+M)
- **Proton Pass** - Password manager (keybind: SUPER+SHIFT+/)
- Discord - Communication (keybind: SUPER+SHIFT+D)

**Configured in Ansible but not installed:**

- Development: GitHub Desktop alternative, GoLand
- Browsers: Chromium, Zen Browser, Firefox, Brave
- Media: Spotify, Audacity
- Communication: Signal, Slack
- Productivity: Obsidian, LibreOffice

### Terminal Applications

- Alacritty - Terminal emulator
- Kitty - Terminal emulator
- btop - System monitor
- lazydocker - Docker TUI (may not be installed)

### System Defaults

- **Browser:** Zen Browser (`zen.desktop`)
- **Terminal:** Uses `xdg-terminal-exec` (system default)
- **Editor:** `nvim` (via `$EDITOR`)
- **File Manager:** Nautilus

## Omarchy Utilities

### Launch Scripts

**omarchy-launch-browser**

- Uses system default browser via `xdg-settings`
- Auto-detects browser type for private mode:
  - Firefox/Zen/LibreWolf: `--private-window`
  - Chrome/Chromium/Brave: `--incognito`

**omarchy-launch-webapp**

- Launches URLs as PWAs using Chromium `--app=` mode
- Creates standalone windows with custom app IDs
- Falls back to Chromium if default browser doesn't support app mode

**omarchy-launch-or-focus**

- Smart launcher that checks if app is running
- Focuses existing window or launches new instance
- Used for: Spotify, Discord, Signal, Obsidian

**omarchy-launch-tui**

- Launches terminal apps with custom app-id
- Format: `org.omarchy.<appname>`
- Used for: btop, lazydocker, nvim

**omarchy-launch-editor**

- Detects editor type from `$EDITOR`
- TUI editors (nvim/vim/nano/micro/hx): Launch in terminal
- GUI editors: Launch directly

## Customization Guide

### Adding New Keybindings

Edit `~/.config/hypr/custom.bindings.conf`:

```conf
# Format: bindd = <modifiers>, <key>, <description>, <action>, <command>

# Launch app directly
bindd = SUPER SHIFT, K, Krita, exec, uwsm-app -- flatpak run org.kde.krita

# Launch or focus existing window
bindd = SUPER SHIFT, S, Slack, exec, omarchy-launch-or-focus ^slack$ "uwsm-app -- slack"

# Launch web app as PWA
bindd = SUPER SHIFT, L, Linear, exec, omarchy-launch-webapp "https://linear.app"

# Launch TUI app in terminal
bindd = SUPER SHIFT, H, Htop, exec, omarchy-launch-tui htop
```

### Adding Autostart Applications

Edit `~/.config/hypr/custom.autostart.conf`:

```conf
exec-once = uwsm-app -- my-app
exec-once = uwsm-app -- flatpak run com.example.App
```

### Customizing Window Rules

Edit `~/.config/hypr/custom.windows.conf`:

```conf
# Float specific window
windowrule = float, ^(my-app)$

# Set size and position
windowrule = size 800 600, ^(my-app)$
windowrule = center, ^(my-app)$

# Workspace assignment
windowrule = workspace 2, ^(my-app)$
```

### Customizing Appearance

Edit `~/.config/hypr/custom.looknfeel.conf` for gaps, borders, shadows, blur, etc.

### Monitor Configuration

Edit `~/.config/hypr/custom.monitors.conf`:

```conf
# Format: monitor = [port], resolution, position, scale
monitor = DP-1, 2560x1440@144, 0x0, 1
monitor = HDMI-A-1, 1920x1080@60, 2560x0, 1
```

## Deployment

This configuration is deployed via **GNU Stow**:

```bash
cd ~/nix-darwin
stow --target=$HOME .config
```

This creates symlinks from `~/.config/` to `~/nix-darwin/.config/`.

## Resources

- [Omarchy Manual](https://learn.omacom.io/2/the-omarchy-manual)
- [Hyprland Wiki](https://wiki.hyprland.org/)
- [Omarchy Themes](https://learn.omacom.io/2/the-omarchy-manual/90/extra-themes)
- [GitHub Repository](https://github.com/yourusername/nix-darwin) _(update with your repo)_

## Notes

- All Omarchy default configs are in `~/.local/share/omarchy/`
- Never edit Omarchy defaults directly - always use custom overlays
- Application launches use `uwsm-app --` for proper Wayland session management
- Web apps with `#` in URL should use `##` to prevent Hyprland comment parsing
- Current working directory for terminal launches uses `omarchy-cmd-terminal-cwd`
