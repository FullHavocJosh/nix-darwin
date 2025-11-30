# Hyprland Configuration Restructure - COMPLETED

## Summary

Successfully restructured the Hyprland configuration to be **Omarchy-compatible** using custom overlay files. This repo contains ONLY your customizations - no KDE-specific or Omarchy stock files.

## Changes Made

### ✅ Custom Configuration Files (Your Customizations)
- `custom.autostart.conf` - Personal autostart applications (empty template)
- `custom.bindings.conf` - Application launcher bindings (empty template)
- `custom.input.conf` - Input customizations (keyboard repeat, touchpad, natural scroll)
- `custom.looknfeel.conf` - Appearance tweaks (blur settings)
- `custom.monitors.conf` - Monitor configuration with 1.6x scaling
- `custom.windows.conf` - Window rules for terminals, browsers, apps, workspaces

### ✅ Stock Files (Minimal with Source Lines)
- `autostart.conf` - Sources `custom.autostart.conf`
- `bindings.conf` - Sources `custom.bindings.conf`
- `input.conf` - Sources `custom.input.conf`
- `looknfeel.conf` - Sources `custom.looknfeel.conf`
- `monitors.conf` - Sources `custom.monitors.conf`

### ✅ Main Configuration
- `hyprland.conf` - Updated with proper Omarchy sourcing order
- `hyprpaper.conf` - Wallpaper configuration

### ✅ Scripts Directory
- `toggle-gaps.sh` - Toggle workspace gaps on/off

### ✅ Removed (Not Needed in Repo)
**Omarchy Stock Files** (these exist in `~/.config/hypr/` from Omarchy):
- `hypridle.conf` - ❌ Not in repo (Omarchy manages this)
- `hyprlock.conf` - ❌ Not in repo (Omarchy manages this)
- `hyprsunset.conf` - ❌ Not in repo (Omarchy manages this)
- `xdph.conf` - ❌ Not in repo (Omarchy manages this)

**KDE-Specific Scripts** (removed):
- `audio-switch.sh` - KDE/kdialog specific
- `get-terminal-cwd.sh` - Konsole specific
- `launch-or-focus.sh` - KDE specific
- `power-menu.sh` - KDE/kdialog specific
- `screen-record.sh` - Spectacle/KDE specific

**Obsolete Directories**:
- `defaults/`, `bindings/`, `apps/`, `locals/`

### ✅ Protected (Won't be stowed)
- `.config/waybar` - Uses Omarchy's waybar
- `.config/hypr.backup.pre-restructure` - Backup of old structure

---

## Sourcing Order (hyprland.conf)

```
1. Omarchy defaults (from ~/.local/share/omarchy/default/hypr/)
   - autostart.conf
   - bindings/media.conf
   - bindings/clipboard.conf
   - bindings/tiling-v2.conf
   - bindings/utilities.conf
   - envs.conf
   - looknfeel.conf
   - input.conf
   - windows.conf
   - theme/hyprland.conf

2. Your customizations (from ~/.config/hypr/)
   - monitors.conf → sources custom.monitors.conf
   - input.conf → sources custom.input.conf
   - bindings.conf → sources custom.bindings.conf
   - looknfeel.conf → sources custom.looknfeel.conf
   - autostart.conf → sources custom.autostart.conf
   - custom.windows.conf
```

---

## How It Works

1. **Omarchy defaults load first** - All base functionality from Omarchy
2. **Stock files load next** - Minimal files that just source your custom configs
3. **Custom files override** - Your `custom.*.conf` files override/extend Omarchy defaults
4. **Clean separation** - Easy to see what's stock vs custom in git diffs
5. **No duplicates** - Omarchy stock files stay managed by Omarchy, not in repo

---

## Benefits

✅ **Omarchy compatible** - Doesn't break Omarchy's core functionality  
✅ **Clean customizations** - All your changes in dedicated `custom.*.conf` files  
✅ **Git-friendly** - Only your customizations tracked, easy diffs  
✅ **No duplication** - Omarchy manages stock files, repo only has your overrides  
✅ **No KDE lock-in** - Removed all KDE-specific customizations  
✅ **Stow-safe** - Won't overwrite critical Omarchy files  
✅ **Maintainable** - Clear separation between stock and custom  

---

## Files That Will Be Stowed

When you run `stow . -t ~`, these files will be linked:

```
.config/hypr/
├── hyprland.conf              # Main config with Omarchy sourcing
├── autostart.conf             # Sources custom.autostart.conf
├── bindings.conf              # Sources custom.bindings.conf
├── input.conf                 # Sources custom.input.conf
├── looknfeel.conf             # Sources custom.looknfeel.conf
├── monitors.conf              # Sources custom.monitors.conf
├── custom.autostart.conf      # YOUR autostart apps
├── custom.bindings.conf       # YOUR app bindings
├── custom.input.conf          # YOUR input settings
├── custom.looknfeel.conf      # YOUR appearance tweaks
├── custom.monitors.conf       # YOUR monitor config
├── custom.windows.conf        # YOUR window rules
├── hyprpaper.conf             # Wallpaper config
└── scripts/
    └── toggle-gaps.sh         # YOUR gap toggle script
```

**NOT stowed** (managed by Omarchy):
- `hypridle.conf` - Omarchy stock
- `hyprlock.conf` - Omarchy stock
- `hyprsunset.conf` - Omarchy stock
- `xdph.conf` - Omarchy stock

---

## Next Steps

1. **Install stow** (if needed):
   ```bash
   sudo dnf install stow
   ```

2. **Apply stow**:
   ```bash
   cd ~/nix-darwin
   stow . -t ~
   ```

3. **Reload Hyprland**:
   ```bash
   hyprctl reload
   ```

---

## Customization Guide

### Adding New Autostart Apps
Edit `custom.autostart.conf`:
```conf
exec-once = syncthing -no-browser
exec-once = nextcloud --background
```

### Adding New Keybindings
Edit `custom.bindings.conf`:
```conf
bindd = SUPER, RETURN, Terminal, exec, alacritty
bindd = SUPER SHIFT, B, Browser, exec, firefox
bindd = SUPER SHIFT, E, Email, exec, firefox --new-window https://mail.google.com
```

### Changing Monitor Setup
Edit `custom.monitors.conf`:
```conf
monitor = DP-1, 2560x1440@144, 0x0, 1
monitor = HDMI-1, 1920x1080@60, 2560x0, 1
```

### Adding Window Rules
Edit `custom.windows.conf`:
```conf
windowrulev2 = workspace 5, class:(myapp)
windowrulev2 = float, class:(calculator)
```

---

## Why No Omarchy Stock Files?

**Question:** Why aren't `hypridle.conf`, `hyprlock.conf`, etc. in the repo?

**Answer:** These are **Omarchy-managed files** that already exist in `~/.config/hypr/` from your Omarchy installation. Including them in the repo would:
- ❌ Create duplicates
- ❌ Potentially override Omarchy updates
- ❌ Add unnecessary maintenance burden

**The repo should only contain YOUR customizations**, not Omarchy's stock configuration.

---

## Backup Location

Original structure backed up to:
`.config/hypr.backup.pre-restructure/`

---

**Restructure completed on:** 2025-11-30  
**Status:** ✅ Ready for stow  
**Philosophy:** Only customizations, no stock files, no KDE lock-in
