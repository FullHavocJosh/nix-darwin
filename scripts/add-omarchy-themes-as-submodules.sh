#!/usr/bin/env bash

# Add curated Omarchy themes as git submodules
# These will be managed in your dotfiles and deployed via stow

set -eo pipefail

cd "$(dirname "$0")"

# Create the themes directory structure
mkdir -p .config/omarchy/themes

# Curated theme list - only the ones you want
declare -A THEMES=(
    ["aetheria"]="https://github.com/JJDizz1L/aetheria"
    ["arc-blueberry"]="https://github.com/vale-c/omarchy-arc-blueberry"
    ["archwave"]="https://github.com/davidguttman/archwave"
    ["aura"]="https://github.com/bjarneo/omarchy-aura-theme"
    ["ayaka"]="https://github.com/abhijeet-swami/omarchy-ayaka-theme"
    ["azure-glow"]="https://github.com/Hydradevx/omarchy-azure-glow-theme"
    ["blackturq"]="https://github.com/HANCORE-linux/omarchy-blackturq-theme"
    ["bluedotrb"]="https://github.com/dotsilva/omarchy-bluedotrb-theme"
    ["blueridge-dark"]="https://github.com/hipsterusername/omarchy-blueridge-dark-theme"
    ["catppuccin-dark"]="https://github.com/Luquatic/omarchy-catppuccin-dark"
    ["citrus-cynapse"]="https://github.com/Grey-007/citrus-cynapse"
    ["demon"]="https://github.com/HANCORE-linux/omarchy-demon-theme"
    ["dotrb"]="https://github.com/dotsilva/omarchy-dotrb-theme"
    ["drac"]="https://github.com/ShehabShaef/omarchy-drac-theme"
    ["dracula"]="https://github.com/catlee/omarchy-dracula-theme"
    ["eldritch"]="https://github.com/eldritch-theme/omarchy"
    ["felix"]="https://github.com/TyRichards/omarchy-felix-theme"
    ["fireside"]="https://github.com/bjarneo/omarchy-fireside-theme"
    ["flexoki-dark"]="https://github.com/euandeas/omarchy-flexoki-dark-theme"
    ["futurism"]="https://github.com/bjarneo/omarchy-futurism-theme"
    ["hakker-green"]="https://github.com/joaquinmeza/omarchy-hakker-green-theme"
    ["mars"]="https://github.com/steve-lohmeyer/omarchy-mars-theme"
    ["midnight"]="https://github.com/JaxonWright/omarchy-midnight-theme"
    ["monokai"]="https://github.com/bjarneo/omarchy-monokai-theme"
    ["neovoid"]="https://github.com/RiO7MAKK3R/omarchy-neovoid-theme"
    ["nes"]="https://github.com/bjarneo/omarchy-nes-theme"
    ["pandora"]="https://github.com/imbypass/omarchy-pandora-theme"
    ["pulsar"]="https://github.com/bjarneo/omarchy-pulsar-theme"
    ["purple-moon"]="https://github.com/Grey-007/purple-moon"
    ["sunset-drive"]="https://github.com/tahayvr/omarchy-sunset-drive-theme"
    ["temerald"]="https://github.com/Ahmad-Mtr/omarchy-temerald-theme"
    ["tokyoled"]="https://github.com/Justin-De-Sio/omarchy-tokyoled-theme"
    ["torrentz-hydra"]="https://github.com/monoooki/omarchy-torrentz-hydra-theme"
    ["waveform-dark"]="https://github.com/hipsterusername/omarchy-waveform-dark-theme"
    ["vhs80"]="https://github.com/tahayvr/omarchy-vhs80-theme"
    ["void"]="https://github.com/vyrx-dev/omarchy-void-theme"
)

echo "=========================================="
echo "Adding Curated Omarchy Themes"
echo "=========================================="
echo "This will add ${#THEME_LIST[@]} selected themes as submodules"
echo "Location: .config/omarchy/themes/"
echo ""

THEME_LIST=(
    "aetheria" "arc-blueberry" "archwave" "aura" "ayaka" "azure-glow"
    "blackturq" "bluedotrb" "blueridge-dark" "catppuccin-dark"
    "citrus-cynapse" "demon" "dotrb" "drac" "dracula" "eldritch"
    "felix" "fireside" "flexoki-dark" "futurism" "hakker-green"
    "mars" "midnight" "monokai" "neovoid" "nes" "pandora" "pulsar"
    "purple-moon" "sunset-drive" "temerald" "tokyoled" "torrentz-hydra"
    "waveform-dark" "vhs80" "void"
)

echo "Themes to add:"
printf "  %s\n" "${THEME_LIST[@]}" | column -c 80
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

ADDED=0
FAILED=0
SKIPPED=0

for theme_name in "${THEME_LIST[@]}"; do
    url="${THEMES[$theme_name]}"
    THEME_PATH=".config/omarchy/themes/$theme_name"
    
    TOTAL=$((ADDED + FAILED + SKIPPED + 1))
    printf "[%d/%d] %s... " "$TOTAL" "${#THEME_LIST[@]}" "$theme_name"
    
    # Check if submodule already exists
    if [ -d "$THEME_PATH" ]; then
        echo "SKIP (exists)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi
    
    # Add as submodule
    if git submodule add --quiet "$url" "$THEME_PATH" 2>/dev/null; then
        echo "OK"
        ADDED=$((ADDED + 1))
    else
        echo "FAIL"
        FAILED=$((FAILED + 1))
    fi
    
    sleep 0.1
done

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Added:   $ADDED"
echo "Skipped: $SKIPPED"
echo "Failed:  $FAILED"
echo ""
echo "Next steps:"
echo "1. Review changes:  git status"
echo "2. Commit changes:  git commit -m 'Add curated Omarchy themes as submodules'"
echo "3. Deploy with stow:"
echo "     cd ~ && stow --target=\$HOME nix-darwin/.config"
echo "   or:"
echo "     cd ~/nix-darwin && stow --target=\$HOME .config"
echo ""
echo "After cloning on a new machine:"
echo "  git submodule update --init --recursive"
echo ""
echo "Switch themes with:"
echo "  omarchy-theme-set <theme-name>"

# ============================================================
# REFERENCE: All Available Omarchy Themes (79 total)
# ============================================================
# To add more themes, copy from this list to the THEMES array above
#
# ["amberbyte"]="https://github.com/tahfizhabib/omarchy-amberbyte-theme"
# ["artzen"]="https://github.com/tahfizhabib/omarchy-artzen-theme"
# ["ash"]="https://github.com/bjarneo/omarchy-ash-theme"
# ["all-hallows-eve"]="https://github.com/guilhermetk/omarchy-all-hallows-eve-theme"
# ["bauhaus"]="https://github.com/somerocketeer/omarchy-bauhaus-theme"
# ["blackgold"]="https://github.com/HANCORE-linux/omarchy-blackgold-theme"
# ["bliss"]="https://github.com/mishonki3/omarchy-bliss-theme"
# ["cobalt2"]="https://github.com/hoblin/omarchy-cobalt2-theme"
# ["darcula"]="https://github.com/noahljungberg/omarchy-darcula-theme"
# ["evergarden"]="https://github.com/celsobenedetti/omarchy-evergarden"
# ["forest-green"]="https://github.com/abhijeet-swami/omarchy-forest-green-theme"
# ["frost"]="https://github.com/bjarneo/omarchy-frost-theme"
# ["gold-rush"]="https://github.com/tahayvr/omarchy-gold-rush-theme"
# ["thegreek"]="https://github.com/HANCORE-linux/omarchy-thegreek-theme"
# ["green-garden"]="https://github.com/kalk-ak/omarchy-green-garden-theme"
# ["infernium"]="https://github.com/RiO7MAKK3R/omarchy-infernium-dark-theme"
# ["mechanoonna"]="https://github.com/HANCORE-linux/omarchy-mechanoonna-theme"
# ["milkmatcha-light"]="https://github.com/hipsterusername/omarchy-milkmatcha-light-theme"
# ["monochrome"]="https://github.com/Swarnim114/omarchy-monochrome-theme"
# ["nagai-poolside"]="https://github.com/somerocketeer/omarchy-nagai-poolside-theme"
# ["neo-sploosh"]="https://github.com/monoooki/omarchy-neo-sploosh-theme"
# ["omacarchy"]="https://github.com/RiO7MAKK3R/omarchy-omacarchy-theme"
# ["one-dark-pro"]="https://github.com/sc0ttman/omarchy-one-dark-pro-theme"
# ["pina"]="https://github.com/bjarneo/omarchy-pina-theme"
# ["pink-blood"]="https://github.com/ITSZXY/pink-blood-omarchy-theme"
# ["purplewave"]="https://github.com/dotsilva/omarchy-purplewave-theme"
# ["retropc"]="https://github.com/rondilley/omarchy-retropc-theme"
# ["rose-pine-dark"]="https://github.com/guilhermetk/omarchy-rose-pine-dark"
# ["roseofdune"]="https://github.com/HANCORE-linux/omarchy-roseofdune-theme"
# ["sakura"]="https://github.com/bjarneo/omarchy-sakura-theme"
# ["sapphire"]="https://github.com/HANCORE-linux/omarchy-sapphire-theme"
# ["shadesofjade"]="https://github.com/HANCORE-linux/omarchy-shadesofjade-theme"
# ["space-monkey"]="https://github.com/TyRichards/omarchy-space-monkey-theme"
# ["snow"]="https://github.com/bjarneo/omarchy-snow-theme"
# ["solarized"]="https://github.com/Gazler/omarchy-solarized-theme"
# ["solarized-light"]="https://github.com/dfrico/omarchy-solarized-light-theme"
# ["solarizedosaka"]="https://github.com/motorsss/omarchy-solarizedosaka-theme"
# ["sunset"]="https://github.com/rondilley/omarchy-sunset-theme"
# ["super-game-bro"]="https://github.com/TyRichards/omarchy-super-game-bro-theme"
# ["synthwave84"]="https://github.com/omacom-io/omarchy-synthwave84-theme"
# ["tycho"]="https://github.com/leonardobetti/omarchy-tycho"
# ["vesper"]="https://github.com/thmoee/omarchy-vesper-theme"
# ["whitegold"]="https://github.com/HANCORE-linux/omarchy-whitegold-theme"
#
# Note: torrentz-hydra repo not found (404)
