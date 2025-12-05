#!/usr/bin/env bash

# Script to install all Nerd Fonts on Linux
# This will download and install popular Nerd Fonts to ~/.local/share/fonts

set -e

FONT_DIR="$HOME/.local/share/fonts/nerd-fonts"
TEMP_DIR="/tmp/nerd-fonts-install"
VERSION="v3.3.0"

# List of popular Nerd Fonts
FONTS=(
    "0xProto"
    "3270"
    "Agave"
    "AnonymousPro"
    "Arimo"
    "AurulentSansMono"
    "BigBlueTerminal"
    "BitstreamVeraSansMono"
    "CascadiaCode"
    "CascadiaMono"
    "CodeNewRoman"
    "ComicShannsMono"
    "CommitMono"
    "Cousine"
    "D2Coding"
    "DaddyTimeMono"
    "DejaVuSansMono"
    "DroidSansMono"
    "EnvyCodeR"
    "FantasqueSansMono"
    "FiraCode"
    "FiraMono"
    "GeistMono"
    "Go-Mono"
    "Gohu"
    "Hack"
    "Hasklig"
    "HeavyData"
    "Hermit"
    "iA-Writer"
    "IBMPlexMono"
    "Inconsolata"
    "InconsolataGo"
    "InconsolataLGC"
    "IntelOneMono"
    "Iosevka"
    "IosevkaTerm"
    "IosevkaTermSlab"
    "JetBrainsMono"
    "Lekton"
    "LiberationMono"
    "Lilex"
    "Martian"
    "Meslo"
    "Monaspace"
    "Monofur"
    "Monoid"
    "Mononoki"
    "MPlus"
    "NerdFontsSymbolsOnly"
    "Noto"
    "OpenDyslexic"
    "Overpass"
    "ProFont"
    "ProggyClean"
    "Recursive"
    "RobotoMono"
    "ShareTechMono"
    "SourceCodePro"
    "SpaceMono"
    "Terminus"
    "Tinos"
    "Ubuntu"
    "UbuntuMono"
    "UbuntuSans"
    "VictorMono"
)

echo "Installing Nerd Fonts..."
echo "========================"
echo ""

# Create directories
mkdir -p "$FONT_DIR"
mkdir -p "$TEMP_DIR"

cd "$TEMP_DIR"

# Counter for progress
total=${#FONTS[@]}
current=0

# Download and install each font
for font in "${FONTS[@]}"; do
    current=$((current + 1))
    echo "[$current/$total] Processing $font..."
    
    # Download font
    if curl -fLo "${font}.zip" \
        "https://github.com/ryanoasis/nerd-fonts/releases/download/${VERSION}/${font}.zip" 2>/dev/null; then
        
        # Create font-specific directory
        mkdir -p "$FONT_DIR/${font}"
        
        # Extract fonts
        if unzip -o -q "${font}.zip" -d "$FONT_DIR/${font}" 2>/dev/null; then
            echo "  ✓ Installed $font"
        else
            echo "  ✗ Failed to extract $font"
        fi
        
        # Clean up zip file
        rm -f "${font}.zip"
    else
        echo "  ✗ Failed to download $font"
    fi
done

echo ""
echo "Updating font cache..."
fc-cache -f "$FONT_DIR"

echo ""
echo "Installation complete!"
echo "========================"
echo ""
echo "Installed fonts in: $FONT_DIR"
echo ""
echo "To verify installation, run:"
echo "  fc-list | grep -i 'nerd' | wc -l"
echo ""
echo "Clean up temporary files with:"
echo "  rm -rf $TEMP_DIR"
