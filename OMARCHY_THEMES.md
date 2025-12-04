# Managing Omarchy Themes with Git Submodules + Stow

This repository can manage Omarchy themes as git submodules, deployed via stow.

## Quick Start

### Option 1: Add Curated Themes (36 selected themes)

```bash
cd ~/nix-darwin
./add-omarchy-themes-as-submodules.sh
```

This adds a curated selection of 36 themes that you've chosen.

### Option 2: Add Individual Themes

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

## Deploy with Stow

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

## Using Themes

Switch themes using:

```bash
omarchy-theme-set <theme-name>
```

Or via the Omarchy menu: `Super+Alt+Space` → Change > Style > Theme

## Updating Themes

Update all theme submodules:

```bash
cd ~/nix-darwin
git submodule update --remote --merge
git commit -am "Update Omarchy themes"
```

## Cloning on a New Machine

After cloning this repo elsewhere:

```bash
git clone <your-repo-url> ~/nix-darwin
cd ~/nix-darwin
git submodule update --init --recursive
stow --target=$HOME .config
```

## Removing a Theme

```bash
cd ~/nix-darwin
git submodule deinit .config/omarchy/themes/<theme-name>
git rm .config/omarchy/themes/<theme-name>
git commit -m "Remove <theme-name> theme"
```

## Curated Theme List (36 themes)

The script adds these themes:

- aetheria, arc-blueberry, archwave, aura, ayaka, azure-glow
- blackturq, bluedotrb, blueridge-dark, catppuccin-dark
- citrus-cynapse, demon, dotrb, drac, dracula, eldritch
- felix, fireside, flexoki-dark, futurism, hakker-green
- mars, midnight, monokai, neovoid, nes, pandora, pulsar
- purple-moon, sunset-drive, temerald, tokyoled, torrentz-hydra
- waveform-dark, vhs80, void

## Structure

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

## See Also

- [Omarchy Themes Documentation](https://learn.omacom.io/2/the-omarchy-manual/90/extra-themes)
- All theme URLs are in: `add-omarchy-themes-as-submodules.sh` (see commented section)
