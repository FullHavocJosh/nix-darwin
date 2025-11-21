# Hyprland Migration Guide (Nobara KDE Edition)

This document provides a complete guide for the Hyprland desktop environment configuration optimized for Nobara Fedora with KDE Plasma integration.

## Overview

The Hyprland configuration has been completely migrated from the Omarchy setup to work seamlessly with Nobara KDE Plasma. This configuration **maximizes use of KDE's built-in tools** (Konsole, Spectacle, Dolphin, etc.) to minimize additional package installations while maintaining full functionality.

### Design Philosophy

- **KDE Integration First**: Use KDE Plasma's built-in tools wherever possible
- **Minimal Packages**: Only install essential Hyprland components
- **Native Notifications**: Leverage KDE's notification system
- **System Consistency**: Match KDE's look and feel with Catppuccin Mocha theme

## Directory Structure

```
.config/hypr/
├── hyprland.conf              # Main configuration file
├── defaults/                  # Default configurations
│   ├── autostart.conf        # Autostart applications
│   ├── envs.conf             # Environment variables
│   ├── input.conf            # Input device settings
│   ├── looknfeel.conf        # Appearance & Catppuccin Mocha theme
│   └── windows.conf          # Window rules
├── bindings/                  # Keybinding configurations
│   ├── tiling.conf           # Window management bindings
│   ├── utilities.conf        # Application launchers & utilities
│   ├── media.conf            # Media control bindings
│   └── clipboard.conf        # Copy/paste bindings
├── apps/                      # App-specific configurations
│   ├── terminals.conf        # Terminal window rules
│   └── browsers.conf         # Browser window rules
├── locals/                    # Machine-specific overrides
│   ├── monitors.conf         # Monitor configuration
│   ├── input.conf            # Input device overrides
│   └── autostart.conf        # Local autostart apps
└── scripts/                   # Helper scripts
    ├── get-terminal-cwd.sh   # Launch terminal in current directory
    ├── launch-or-focus.sh    # Focus existing window or launch app
    ├── toggle-gaps.sh        # Toggle workspace gaps
    ├── audio-switch.sh       # Switch between audio outputs
    ├── power-menu.sh         # Power management menu
    └── screen-record.sh      # Screen recording utility

.config/waybar/
├── config.jsonc               # Waybar configuration
└── style.css                  # Catppuccin Mocha styling
```

## Package Requirements for Nobara KDE

### What's Already Included in Nobara KDE

Nobara KDE comes pre-installed with these tools that our configuration uses:

- **Terminal**: Konsole
- **File Manager**: Dolphin
- **Text Editor**: Kate
- **Screenshots**: Spectacle (with video recording in Plasma 6+)
- **Calculator**: KCalc
- **Color Picker**: KColorChooser
- **Notifications**: KDE Plasma notifications (knotifications)
- **Clipboard**: Klipper (KDE's built-in clipboard manager)
- **Auth Agent**: polkit-kde-authentication-agent
- **Audio**: PipeWire, WirePlumber, wpctl
- **Media Control**: playerctl
- **Brightness**: brightnessctl
- **Clipboard Utils**: wl-clipboard
- **JSON Parser**: jq

### Essential Hyprland Packages (Required)

These are the **only** packages you need to install:

```bash
sudo dnf install -y \
    hyprland \
    hyprlock \
    hypridle \
    hyprpaper \
    waybar
```

That's it! Only **5 packages** needed.

### Optional Enhancements (Not Required)

If you prefer alternatives to KDE tools:

```bash
# Alternative launcher (instead of KRunner)
sudo dnf install -y rofi-wayland

# Alternative terminal (instead of Konsole)
sudo dnf install -y alacritty

# Alternative screen recording (for older Plasma versions without Spectacle video)
sudo dnf install -y obs-studio  # Usually pre-installed on Nobara
```

### Font Requirements

```bash
sudo dnf install -y \
    fontawesome-fonts \
    fontawesome-fonts-web \
    google-noto-emoji-fonts
```

Install CaskaydiaCove Nerd Font from [Nerd Fonts](https://www.nerdfonts.com/):

```bash
mkdir -p ~/.local/share/fonts
cd ~/.local/share/fonts
curl -OL https://github.com/ryanoasis/nerd-fonts/releases/latest/download/CascadiaCode.tar.xz
tar -xf CascadiaCode.tar.xz
fc-cache -fv
```

## Key Replacements from Omarchy

| Omarchy Command                          | Nobara KDE Replacement                                               |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `omarchy-launch-walker`                  | `krunner` (KDE's built-in launcher)                                  |
| `omarchy-menu`                           | `qdbus org.kde.ksmserver /KSMServer logout 1 -1 -1`                  |
| `omarchy-cmd-screenshot`                 | `spectacle --region --output ~/Pictures/Screenshots`                 |
| `omarchy-cmd-screenrecord`               | `spectacle --record region` (Plasma 6+) or `obs-studio`              |
| `omarchy-toggle-waybar`                  | `killall -SIGUSR1 waybar`                                            |
| `omarchy-hyprland-workspace-toggle-gaps` | `~/.config/hypr/scripts/toggle-gaps.sh`                              |
| `omarchy-cmd-audio-switch`               | `~/.config/hypr/scripts/audio-switch.sh` (uses wpctl)                |
| `omarchy-launch-walker -m clipboard`     | `qdbus org.kde.klipper /klipper showKlipperManuallyInvokeActionMenu` |
| Color picker                             | `kcolorchooser`                                                      |
| Notifications                            | `qdbus org.freedesktop.Notifications` (KDE notifications)            |
| Nightlight                               | KDE Night Color (Settings > Display)                                 |

## Installation Steps

1. **Install required packages** (see above)

2. **Make scripts executable**:

   ```bash
   chmod +x ~/.config/hypr/scripts/*.sh
   ```

3. **Create required directories**:

   ```bash
   mkdir -p ~/Pictures/Screenshots
   mkdir -p ~/Videos/Recordings
   ```

4. **Set wallpaper** (edit `hyprpaper.conf`):

   ```bash
   # Edit ~/.config/hypr/hyprpaper.conf
   preload = ~/.wallpapers/your-wallpaper.jpg
   wallpaper = ,~/.wallpapers/your-wallpaper.jpg
   ```

5. **Configure monitors** (edit `locals/monitors.conf`):

   ```conf
   # Example for dual monitor setup
   monitor = eDP-1, 1920x1080@60, 0x0, 1
   monitor = HDMI-A-1, 2560x1440@144, 1920x0, 1
   ```

6. **Launch Hyprland**:
   - Add to `~/.bash_profile` or `~/.zprofile`:
     ```bash
     if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" = 1 ]; then
       exec Hyprland
     fi
     ```

## Catppuccin Mocha Theme

The entire setup uses the Catppuccin Mocha color palette:

### Color Palette

- **Base**: `#1e1e2e` (background)
- **Text**: `#cdd6f4` (foreground)
- **Mauve**: `#cba6f7` (primary accent)
- **Blue**: `#89b4fa`
- **Sky**: `#89dceb`
- **Green**: `#a6e3a1`
- **Yellow**: `#f9e2af`
- **Red**: `#f38ba8`

Colors are defined in:

- `defaults/looknfeel.conf` for Hyprland
- `waybar/style.css` for Waybar

## Key Bindings Reference

### Application Launchers

- `SUPER + SPACE` - Application launcher (KRunner)
- `SUPER + RETURN` - Terminal (Konsole)
- `SUPER + E` - File manager (Dolphin)
- `SUPER + B` - Browser (Firefox)

### Window Management

- `SUPER + W` - Close window
- `SUPER + T` - Toggle floating
- `SUPER + F` - Fullscreen
- `SUPER + J` - Toggle split
- `SUPER + Arrow Keys` - Move focus
- `SUPER + SHIFT + Arrow Keys` - Swap windows
- `SUPER + 1-9` - Switch workspace
- `SUPER + SHIFT + 1-9` - Move window to workspace

### System Controls

- `SUPER + ESCAPE` - Power menu
- `SUPER + BACKSLASH` - Lock screen
- `SUPER + SHIFT + Q` - Exit Hyprland
- `SUPER + COMMA` - Dismiss notification
- `SUPER + SHIFT + COMMA` - Dismiss all notifications

### Screenshots & Recording

- `PRINT` - Screenshot with selection (Spectacle)
- `SHIFT + PRINT` - Screenshot to clipboard (Spectacle)
- `CTRL + PRINT` - Full screen screenshot (Spectacle)
- `ALT + PRINT` - Screen recording (Spectacle/OBS)
- `SUPER + PRINT` - Color picker (KColorChooser)

### Media Controls

- `XF86AudioRaiseVolume` - Volume up
- `XF86AudioLowerVolume` - Volume down
- `XF86AudioMute` - Toggle mute
- `XF86MonBrightnessUp/Down` - Brightness
- `XF86AudioPlay/Pause` - Media playback

### Utilities

- `SUPER + SHIFT + SPACE` - Toggle waybar
- `SUPER + SHIFT + BACKSPACE` - Toggle gaps
- `SUPER + CTRL + V` - Clipboard history (Klipper)
- `SUPER + CTRL + N` - Toggle nightlight (KDE Night Color via qdbus)

## Waybar Modules

The Waybar configuration includes:

**Left**: Launcher, Workspaces, Window Title  
**Center**: Clock with calendar  
**Right**: System Tray, Bluetooth, Network, Audio, CPU, Memory, Temperature, Battery, Power

All modules are styled with Catppuccin Mocha colors and include hover effects.

## Customization

### Adding Custom Scripts

Place custom scripts in `~/.config/hypr/scripts/` and make them executable:

```bash
chmod +x ~/.config/hypr/scripts/your-script.sh
```

### Machine-Specific Settings

Use files in `locals/` for machine-specific configurations:

- `locals/monitors.conf` - Monitor setup
- `locals/input.conf` - Input device settings
- `locals/autostart.conf` - Additional autostart apps

### Theme Customization

To change from Catppuccin Mocha to another variant:

1. Update color definitions in `defaults/looknfeel.conf`
2. Update color variables in `waybar/style.css`

## Troubleshooting

### Waybar not starting

```bash
killall waybar
waybar &
```

### Scripts not working

Ensure scripts are executable:

```bash
chmod +x ~/.config/hypr/scripts/*.sh
```

### No audio output switching

Install PipeWire and WirePlumber:

```bash
sudo dnf install pipewire wireplumber
systemctl --user enable --now pipewire pipewire-pulse wireplumber
```

### Screenshots not working

Spectacle should be pre-installed. If not:

```bash
sudo dnf install spectacle
```

### Clipboard history not working

Klipper should start automatically with KDE. If not:

```bash
klipper &
```

### KRunner not launching

Restart KRunner:

```bash
killall krunner
krunner &
```

## Additional Resources

- [Hyprland Wiki](https://wiki.hyprland.org/)
- [Waybar Documentation](https://github.com/Alexays/Waybar/wiki)
- [Catppuccin Theme](https://github.com/catppuccin/catppuccin)
- [Rofi Documentation](https://github.com/davatorium/rofi)

## Migration Notes

This configuration is optimized for Nobara KDE with the following improvements:

1. **Minimal Packages**: Only 5 packages needed - everything else uses KDE defaults
2. **KDE Integration**: Leverages Konsole, Spectacle, Dolphin, Klipper, KRunner
3. **Native Audio**: Uses wpctl/PipeWire already configured in Nobara
4. **Native Notifications**: KDE Plasma notifications via qdbus
5. **Theme Consistency**: Catppuccin Mocha throughout
6. **Modular Structure**: Easy to customize per-machine
7. **Better Documentation**: Clear organization and comments

### Why This Approach?

**Before (Traditional Hyprland)**: 20+ packages to install  
**After (Nobara KDE Integration)**: 5 packages to install

By using KDE's built-in tools, you get:

- Faster installation
- Better system integration
- Consistent look and feel
- Less maintenance
- Familiar KDE tools you already know

All functionality from Omarchy has been preserved while making the setup more maintainable, portable, and Nobara-optimized.
