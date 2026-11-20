{ pkgs, lib, ... }:
let
  # Upstream Apple Silicon release, pinned by version and hash.
  # dontFixup keeps the ad-hoc code signature intact (fixup would rewrite binaries and break it).
  clipcascade = pkgs.stdenvNoCC.mkDerivation {
    pname = "clipcascade";
    version = "3.5.1";

    src = pkgs.fetchurl {
      url = "https://github.com/Sathvik-Rao/ClipCascade/releases/download/v3.5.1/ClipCascade-Apple_macOS.ARM_M-Series.zip";
      hash = "sha256-lXk8ubmykha2a4PTfXrU6Cx0qkh7TVqU9zSeD03qCHo=";
    };

    nativeBuildInputs = [ pkgs.unzip ];
    sourceRoot = ".";
    dontFixup = true;

    # The zip holds ClipCascade/ClipCascade.app, help.txt and LICENSE.
    installPhase = ''
      runHook preInstall
      mkdir -p $out/Applications
      cp -R ClipCascade/ClipCascade.app $out/Applications/
      runHook postInstall
    '';

    meta.platforms = [ "aarch64-darwin" ];
  };

  # The client derives the E2EE key from the login password, so only the UI login can set it.
  # This helper prints the password from Doppler for pasting (--copy puts it on the clipboard).
  clipcascadePassword = pkgs.writeShellScriptBin "clipcascade-password" ''
    DOPPLER_BIN="/opt/homebrew/bin/doppler"
    if [ ! -x "$DOPPLER_BIN" ]; then
      echo "clipcascade-password: doppler not found at $DOPPLER_BIN" >&2
      exit 1
    fi

    # MacBookM2Pro -> root_macbook, MacMiniM1 -> root_macmini
    HOSTNAME=$(scutil --get LocalHostName)
    case "$HOSTNAME" in
      MacBookM2Pro*)
        DOPPLER_CONFIG_NAME="root_macbook"
        ;;
      MacMiniM1*)
        DOPPLER_CONFIG_NAME="root_macmini"
        ;;
      *)
        echo "clipcascade-password: unknown hostname '$HOSTNAME', cannot determine Doppler config" >&2
        exit 1
        ;;
    esac

    if ! PASSWORD=$("$DOPPLER_BIN" secrets get CLIPCASCADE_PASSWORD --project FullHavocJosh --config "$DOPPLER_CONFIG_NAME" --plain) || [ -z "$PASSWORD" ]; then
      echo "clipcascade-password: CLIPCASCADE_PASSWORD is unset in Doppler config $DOPPLER_CONFIG_NAME" >&2
      exit 1
    fi

    if [ "$1" = "--copy" ]; then
      printf '%s' "$PASSWORD" | /usr/bin/pbcopy
      echo "clipcascade-password: copied to clipboard" >&2
    else
      printf '%s\n' "$PASSWORD"
    fi
  '';
in
{
  environment.systemPackages = [
    clipcascade
    clipcascadePassword
  ];

  # Start the client at login. Must be a user LaunchAgent so it runs in the GUI session
  # (clipboard access needs it). Relaunch only after a failed exit, not after a normal quit.
  launchd.user.agents.clipcascade.serviceConfig = {
    Label = "org.nixos.clipcascade";
    ProgramArguments = [ "/Applications/Nix Apps/ClipCascade.app/Contents/MacOS/ClipCascade" ];
    RunAtLoad = true;
    KeepAlive.SuccessfulExit = false;
    ProcessType = "Interactive";
    StandardOutPath = "/tmp/clipcascade.log";
    StandardErrorPath = "/tmp/clipcascade.error.log";
  };

  # Seed the non-secret server settings once. The user enters credentials once in the client UI,
  # and the app rewrites DATA itself, so nix never overwrites an existing file.
  # Never write username, password, hash or the E2EE key here.
  system.activationScripts.postActivation.text = lib.mkAfter ''
    clipcascade_data="/Users/havoc/Library/Application Support/ClipCascade/DATA"
    if [ ! -e "$clipcascade_data" ]; then
      echo "seeding ClipCascade settings..." >&2
      sudo -u havoc mkdir -p "$(dirname "$clipcascade_data")"
      sudo -u havoc tee "$clipcascade_data" > /dev/null <<'EOF'
    {
      "server_url": "https://clip.rollet.family",
      "websocket_url": "wss://clip.rollet.family/clipsocket",
      "cipher_enabled": true,
      "save_password": false,
      "use_keyring": true
    }
    EOF
    fi
  '';
}
