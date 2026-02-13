{ pkgs, ... }:
let
  # VPN Network Manager Script
  vpnNetworkManager = pkgs.writeShellScript "vpn-network-manager" ''
    #!/usr/bin/env bash
    #
    # VPN Network Manager
    # Automatically connects to VPN when NOT on trusted networks
    #

    # Configuration
    TRUSTED_NETWORKS=("VoidSlip")  # Networks where VPN should NOT connect
    VPN_CONFIG="/Users/havoc/Library/Mobile Documents/com~apple~CloudDocs/Downloads/OpenVPN_Server___vpn_rollet_family_macbookpro.ovpn"
    WIFI_INTERFACE="en0"
    LOG_FILE="/tmp/vpn-network-manager.log"
    PID_FILE="/tmp/openvpn.pid"

    # Logging function
    log() {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
    }

    # Get current WiFi network
    get_current_network() {
        local network=$(/usr/sbin/networksetup -getairportnetwork "$WIFI_INTERFACE" 2>/dev/null | sed 's/Current Wi-Fi Network: //')
        if [[ "$network" == "You are not associated with an AirPort network." ]] || [[ -z "$network" ]]; then
            echo ""
        else
            echo "$network"
        fi
    }

    # Check if VPN is running
    is_vpn_running() {
        if [[ -f "$PID_FILE" ]]; then
            local pid=$(cat "$PID_FILE")
            if ps -p "$pid" > /dev/null 2>&1; then
                return 0  # VPN is running
            else
                rm -f "$PID_FILE"
            fi
        fi
        return 1  # VPN is not running
    }

    # Check if current network is trusted
    is_trusted_network() {
        local current_network="$1"
        for trusted in "''${TRUSTED_NETWORKS[@]}"; do
            if [[ "$current_network" == "$trusted" ]]; then
                return 0  # Is trusted
            fi
        done
        return 1  # Not trusted
    }

    # Start VPN
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

    # Stop VPN
    stop_vpn() {
        if ! is_vpn_running; then
            log "VPN not running"
            return 0
        fi
        
        log "Stopping VPN connection..."
        local pid=$(cat "$PID_FILE")
        kill "$pid" 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        log "VPN stopped"
    }

    # Check if we have any active network connection on en0
    has_network_connection() {
        # Check if en0 has an IPv4 address (not link-local, not loopback)
        local ip=$(ifconfig en0 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')
        if [[ -n "$ip" ]]; then
            return 0  # Has IP address
        fi
        return 1  # No IP address
    }

    # Main logic
    main() {
        local current_network=$(get_current_network)
        
        # First, check if we have any network connection at all
        if ! has_network_connection; then
            log "No network connection on en0"
            stop_vpn
            return
        fi
        
        # We have a network connection
        # If it's a traditional WiFi network with a name, check if it's trusted
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
            # Network connection but no WiFi name (mobile hotspot, ethernet, etc)
            log "On non-WiFi connection (mobile/ethernet) - ensuring VPN is running"
            start_vpn
        fi
    }

    # Main logic
    main() {
        local current_network=$(get_current_network)
        
        # Check if we have any network connection
        if [[ -z "$current_network" ]]; then
            # No traditional WiFi, check for mobile hotspot/tethering
            if is_on_mobile_connection; then
                log "On mobile/tethered connection (not traditional WiFi) - ensuring VPN is running"
                start_vpn
                return
            else
                log "No network connection detected"
                stop_vpn
                return
            fi
        fi
        
        log "Current network: $current_network"
        
        if is_trusted_network "$current_network"; then
            log "On trusted network ($current_network) - ensuring VPN is stopped"
            stop_vpn
        else
            log "On untrusted network ($current_network) - ensuring VPN is running"
            start_vpn
        fi
    }

    # Run main function
    main
  '';
in
{

  ###########################################
  ### MacOS Settings for Personal Devices ###
  ###########################################

  system.activationScripts.script.text = ''
    #!/usr/bin/env bash
    echo "Stowing dotfiles as user $(whoami)..."
    cd "/Users/havoc/nix-darwin" || { echo "Failed to cd into /Users/havoc/nix-darwin"; exit 1; }
    ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow dotfiles"; exit 1; }
    echo "Finished Stowing dotfiles..."

    echo "Setting wallpaper..."
    osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "/Users/havoc/.wallpapers/wallhaven-2yxj8m.jpg"'
  '';

  # Configure Ollama service to listen on all interfaces
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

  # VPN Network Manager - Automatically connect when NOT on VoidSlip WiFi
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

  # System Settings for macOS
  # Documentation at: mynixos.com and look for nix-services
  system.defaults = {
    dock.persistent-apps = [
      "/Applications/Alacritty.app"
    ];
  };
  homebrew = {
    enable = true;
    taps = [
    ];
    # Install Brew Formulas
    brews = [
    ];
    # Install Brew Casks
    casks = [
      "battle-net"
      "curseforge"
      "discord"
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
    # Install App Store Apps, search for ID with "mas search "
    # You must be logged into the Apps Store, and you must have purchased the app
    masApps = {
    };
  };
}
