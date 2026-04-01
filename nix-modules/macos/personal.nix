{ pkgs, ... }:
let
  vpnNetworkManager = pkgs.writeShellScript "vpn-network-manager" ''
    #!/usr/bin/env bash

    TRUSTED_NETWORKS=("VoidSlip")
    VPN_CONFIG="/Users/havoc/Library/Mobile Documents/com~apple~CloudDocs/Downloads/OpenVPN_Server___vpn_rollet_family_macbookpro.ovpn"
    WIFI_INTERFACE="en0"
    LOG_FILE="/tmp/vpn-network-manager.log"
    PID_FILE="/tmp/openvpn.pid"

    log() {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
    }

    get_current_network() {
        local network=$(/usr/sbin/networksetup -getairportnetwork "$WIFI_INTERFACE" 2>/dev/null | sed 's/Current Wi-Fi Network: //')
        if [[ "$network" == "You are not associated with an AirPort network." ]] || [[ -z "$network" ]]; then
            echo ""
        else
            echo "$network"
        fi
    }

    is_vpn_running() {
        if [[ -f "$PID_FILE" ]]; then
            local pid=$(cat "$PID_FILE")
            if ps -p "$pid" > /dev/null 2>&1; then
                return 0
            else
                rm -f "$PID_FILE"
            fi
        fi
        return 1
    }

    is_trusted_network() {
        local current_network="$1"
        for trusted in "''${TRUSTED_NETWORKS[@]}"; do
            if [[ "$current_network" == "$trusted" ]]; then
                return 0
            fi
        done
        return 1
    }

    start_vpn() {
        if is_vpn_running; then
            log "VPN already running"
            return 0
        fi

        if [[ ! -f "$VPN_CONFIG" ]]; then
            log "ERROR: VPN config file not found: $VPN_CONFIG"
            return 1
        fi

        log "Starting VPN connection..."
        ${pkgs.openvpn}/bin/openvpn --config "$VPN_CONFIG" \
            --daemon \
            --writepid "$PID_FILE" \
            --log "/tmp/openvpn.log" \
            --script-security 2 \
            --setenv PATH '/usr/bin:/bin:/usr/sbin:/sbin' \
            --dhcp-option DNS 192.168.144.1 \
            --dhcp-option DOMAIN rollet.family \
            --up '/bin/sh -c "/usr/sbin/networksetup -setdnsservers Wi-Fi 192.168.144.1 && /usr/sbin/networksetup -setsearchdomains Wi-Fi rollet.family"' \
            --down '/bin/sh -c "/usr/sbin/networksetup -setdnsservers Wi-Fi Empty && /usr/sbin/networksetup -setsearchdomains Wi-Fi Empty"'

        if [[ $? -eq 0 ]]; then
            log "VPN started successfully with DNS 192.168.144.1 and search domain rollet.family"
            return 0
        else
            log "ERROR: Failed to start VPN"
            return 1
        fi
    }

    stop_vpn() {
        if ! is_vpn_running; then
            log "VPN not running"
            return 0
        fi

        log "Stopping VPN connection..."
        local pid=$(cat "$PID_FILE")
        kill "$pid" 2>/dev/null
        sleep 2

        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null
        fi

        rm -f "$PID_FILE"
        log "VPN stopped"
    }

    has_network_connection() {
        local ip=$(ifconfig en0 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')
        if [[ -n "$ip" ]]; then
            return 0
        fi
        return 1
    }

    main() {
        local current_network=$(get_current_network)

        if ! has_network_connection; then
            log "No network connection on en0"
            stop_vpn
            return
        fi

        if [[ -n "$current_network" ]]; then
            log "Current WiFi network: $current_network"
            if is_trusted_network "$current_network"; then
                log "On trusted network ($current_network) - ensuring VPN is stopped"
                stop_vpn
            else
                log "On untrusted WiFi network ($current_network) - ensuring VPN is running"
                start_vpn
            fi
        else
            log "On non-WiFi connection (mobile/ethernet) - ensuring VPN is running"
            start_vpn
        fi
    }

    main
  '';
in
{
  system.activationScripts.script.text = ''
    #!/usr/bin/env bash
    echo "Stowing dotfiles as user $(whoami)..."
    cd "/Users/havoc/nix-darwin" || { echo "Failed to cd into /Users/havoc/nix-darwin"; exit 1; }
    ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow dotfiles"; exit 1; }
    echo "Finished Stowing dotfiles..."

    echo "Patching opencode.json with correct home path..."
    ${pkgs.gnused}/bin/sed -i "s|__HOME__|$HOME|g" "$HOME/.config/opencode/opencode.json"

    echo "Setting wallpaper..."
    osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "/Users/havoc/.wallpapers/wallhaven-1k9m9w.jpg"'
  '';

  launchd.user.agents.ollama = {
    serviceConfig = {
      ProgramArguments = [
        "/Applications/Ollama.app/Contents/Resources/ollama"
        "serve"
      ];
      EnvironmentVariables = {
        OLLAMA_HOST = "0.0.0.0:11434";
        OLLAMA_FLASH_ATTENTION = "1";
        OLLAMA_KV_CACHE_TYPE = "q8_0";
      };
      KeepAlive = true;
      RunAtLoad = true;
      StandardOutPath = "/tmp/ollama.log";
      StandardErrorPath = "/tmp/ollama.error.log";
      LimitLoadToSessionType = [
        "Aqua"
        "Background"
        "LoginWindow"
        "StandardIO"
        "System"
      ];
    };
  };

  launchd.daemons.vpn-network-manager = {
    script = ''
      ${vpnNetworkManager}
    '';
    serviceConfig = {
      RunAtLoad = true;
      StandardOutPath = "/tmp/vpn-network-manager-launchd.log";
      StandardErrorPath = "/tmp/vpn-network-manager-launchd-error.log";
      WatchPaths = [
        "/Library/Preferences/SystemConfiguration"
      ];
      ThrottleInterval = 10;
    };
  };

  system.defaults = {
    dock.persistent-apps = [ ];
  };
  homebrew = {
    enable = true;
    taps = [ ];
    brews = [
      "k9s"
    ];
    casks = [
      "battle-net"
      "curseforge"
      "element"
      "obsidian"
      "ollama-app"
      "plex"
      "plexamp"
      "proton-drive"
      "protonvpn"
      "proton-mail"
      "rustdesk"
      "steam"
      "whisky"
    ];
    masApps = { };
  };
}
