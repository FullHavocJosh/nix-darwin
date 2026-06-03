{
  pkgs,
  lib,
  username,
  ...
}:
let
  openchamberLauncher = pkgs.writeShellScript "openchamber-launcher-wrapper" ''
    #!/usr/bin/env bash
    source "$HOME/.zshrc_envvars" 2>/dev/null || true

    # Add Homebrew to PATH for openchamber to find node
    export PATH="/opt/homebrew/bin:/opt/homebrew/opt/node@22/bin:$PATH"

    PASSWORD_FILE="$HOME/.config/openchamber/.ui-password"
    if [ ! -f "$PASSWORD_FILE" ] || [ ! -s "$PASSWORD_FILE" ]; then
      echo '[openchamber] ERROR: password file missing or empty at ~/.config/openchamber/.ui-password — refusing to start' >&2
      exit 1
    fi
    UI_PASSWORD=$(cat "$PASSWORD_FILE")
    export OPENCHAMBER_UI_PASSWORD="$UI_PASSWORD"

    # Use Homebrew openchamber if available, otherwise fall back to npm-installed version
    if [ -x "/opt/homebrew/bin/openchamber" ]; then
      exec /opt/homebrew/bin/openchamber --foreground --host 0.0.0.0 --port 3000
    elif [ -x "$HOME/.local/bin/openchamber" ]; then
      exec "$HOME/.local/bin/openchamber" --foreground --host 0.0.0.0 --port 3000
    else
      echo '[openchamber] ERROR: openchamber binary not found in /opt/homebrew/bin or ~/.local/bin' >&2
      exit 1
    fi
  '';
in
{
  system.activationScripts.openchamberUserConfig.text = lib.mkAfter ''

    mkdir -p "$HOME/Library/Logs/openchamber"

    # Symlink the Nix-store-built launcher into ~/.local/bin so both this path
    # and the launchd agent point to the same script — no duplication.
    mkdir -p "$HOME/.local/bin"
    ln -sf "${openchamberLauncher}" "$HOME/.local/bin/openchamber-launcher"

    (
      if ! command -v openchamber &>/dev/null; then
        echo "Installing openchamber..."
        # Use Node.js v22 from Homebrew for better-sqlite3 compatibility
        export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
        
        OPENCHAMBER_INSTALL_SCRIPT=$(mktemp)
        # Pinned to commit 3d548a3a526d8fe86fd76d5fef6426cb173b8e57 — update commit and checksum together when upgrading
        curl -fsSL https://raw.githubusercontent.com/openchamber/openchamber/3d548a3a526d8fe86fd76d5fef6426cb173b8e57/scripts/install.sh -o "$OPENCHAMBER_INSTALL_SCRIPT"
        # Pinned SHA-256 for the above commit — recompute with: shasum -a 256 install.sh
        EXPECTED_SHA256="aa268c96ddc6d7d53fc54d2e5c2312e689493ecef6ba4f69730a93d50cf33287"
        ACTUAL_SHA256="$(shasum -a 256 "$OPENCHAMBER_INSTALL_SCRIPT" | awk '{print $1}')"
        if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
          echo "ERROR: openchamber install script checksum mismatch — aborting" >&2
          rm -f "$OPENCHAMBER_INSTALL_SCRIPT"
          exit 1
        fi
        # Script is pinned by commit and checksum-verified above.
        # It installs the openchamber binary to ~/.local/bin — review the pinned
        # commit before bumping the version to confirm no new system modifications.
        bash "$OPENCHAMBER_INSTALL_SCRIPT"
        rm -f "$OPENCHAMBER_INSTALL_SCRIPT"
      fi
    ) || echo "WARNING: openchamber install failed — continuing activation" >&2

    (
      OPENCHAMBER_APP="/Applications/OpenChamber.app"
      if [ ! -d "$OPENCHAMBER_APP" ]; then
        echo "Installing OpenChamber desktop app..."
        # Pinned version — update OC_PINNED_VERSION and the arch-specific checksums together when upgrading.
        # Recompute checksums with: curl -fsSL <dmg-url> | shasum -a 256
        OC_PINNED_VERSION="v1.9.9"
        OC_VERSION_NUM="1.9.9"
        ARCH=$(uname -m)
        case "$ARCH" in
          x86_64) OC_ARCH="x86_64"; OC_PINNED_SHA256="ae73f8d11401bc2b87e112a51ba01ea9dab89e7fa4912f654300926cc255c58b" ;;
          arm64)  OC_ARCH="aarch64"; OC_PINNED_SHA256="1a45ea8d10462a80d2cd7a6c15d238c2c1efd62cd81a63e6128469894ae77826" ;;
          *)      echo "ERROR: Unsupported architecture: $ARCH" >&2; exit 1 ;;
        esac
        OPENCHAMBER_DMG_URL="https://github.com/openchamber/openchamber/releases/download/$OC_PINNED_VERSION/OpenChamber_''${OC_VERSION_NUM}_darwin-''${OC_ARCH}.dmg"
        echo "Downloading OpenChamber $OC_PINNED_VERSION ($OC_ARCH)..."
        OPENCHAMBER_TMPDIR=$(mktemp -d)
        curl -fsSL "$OPENCHAMBER_DMG_URL" -o "$OPENCHAMBER_TMPDIR/OpenChamber.dmg"
        OC_ACTUAL=$(shasum -a 256 "$OPENCHAMBER_TMPDIR/OpenChamber.dmg" | awk '{print $1}')
        if [ "$OC_ACTUAL" != "$OC_PINNED_SHA256" ]; then
          echo "ERROR: OpenChamber DMG checksum mismatch — aborting install" >&2
          rm -rf "$OPENCHAMBER_TMPDIR"
          exit 1
        fi
        MOUNT="$OPENCHAMBER_TMPDIR/mnt"
        mkdir -p "$MOUNT"
        hdiutil attach "$OPENCHAMBER_TMPDIR/OpenChamber.dmg" -nobrowse -mountpoint "$MOUNT" || { echo "ERROR: Failed to mount OpenChamber DMG" >&2; rm -rf "$OPENCHAMBER_TMPDIR"; exit 1; }
        [ -d "$MOUNT/OpenChamber.app" ] || { echo "ERROR: OpenChamber.app not found in mounted DMG at $MOUNT" >&2; hdiutil detach "$MOUNT" -quiet; rm -rf "$OPENCHAMBER_TMPDIR"; exit 1; }
        cp -R "$MOUNT/OpenChamber.app" /Applications/
        hdiutil detach "$MOUNT" -quiet
        rm -rf "$OPENCHAMBER_TMPDIR"
        echo "OpenChamber desktop app installed."
      fi
    ) || echo "WARNING: OpenChamber DMG install failed — continuing activation" >&2

  '';

  launchd.daemons.openchamber = {
    serviceConfig = {
      UserName = username;
      # The wrapper script reads the password at runtime — never a static string in ps aux output.
      ProgramArguments = [
        "/bin/bash"
        "${openchamberLauncher}"
      ];
      KeepAlive = true;
      ThrottleInterval = 30;
      RunAtLoad = true;
      StandardOutPath = "/Users/${username}/Library/Logs/openchamber/openchamber.log";
      StandardErrorPath = "/Users/${username}/Library/Logs/openchamber/openchamber.error.log";
    };
  };
}
