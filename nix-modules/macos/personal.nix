{ pkgs, ... }:
{
  system.activationScripts.script.text = ''
            #!/usr/bin/env bash
            echo "Stowing dotfiles as user $(whoami)..."
            cd "/Users/havoc/nix-darwin" || { echo "Failed to cd into /Users/havoc/nix-darwin"; exit 1; }
            ${pkgs.stow}/bin/stow -R . || { echo "Failed to stow dotfiles"; exit 1; }
            echo "Finished Stowing dotfiles..."

            echo "Setting wallpaper..."
            osascript -e 'tell application "System Events" to set picture of every desktop to POSIX file "/Users/havoc/.wallpapers/wallhaven-1k9m9w.jpg"'

            echo "Syncing HostName to LocalHostName..."
            scutil --set HostName "$(scutil --get LocalHostName)"

            echo "Installing OpenVPN LaunchDaemon..."
            cat > /Library/LaunchDaemons/homebrew.mxcl.openvpn.plist << 'PLIST'
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
    	<key>KeepAlive</key>
    	<true/>
    	<key>Label</key>
    	<string>homebrew.mxcl.openvpn</string>
    	<key>ProgramArguments</key>
    	<array>
    		<string>/opt/homebrew/opt/openvpn/sbin/openvpn</string>
    		<string>--config</string>
    		<string>/opt/homebrew/etc/openvpn/openvpn.conf</string>
    	</array>
    	<key>RunAtLoad</key>
    	<true/>
    	<key>ThrottleInterval</key>
    	<integer>30</integer>
    	<key>WorkingDirectory</key>
    	<string>/opt/homebrew/etc/openvpn</string>
    </dict>
    </plist>
    PLIST
            chown root:wheel /Library/LaunchDaemons/homebrew.mxcl.openvpn.plist
            chmod 644 /Library/LaunchDaemons/homebrew.mxcl.openvpn.plist

            echo "Setting up OpenVPN helper scripts and config..."
            mkdir -p /opt/homebrew/etc/openvpn
            chown root:wheel /opt/homebrew/etc/openvpn
            chmod 755 /opt/homebrew/etc/openvpn

            cat > /opt/homebrew/etc/openvpn/up.sh.new << 'SCRIPT'
    #!/bin/sh
    /usr/sbin/networksetup -setdnsservers Wi-Fi 192.168.144.1
    /usr/sbin/networksetup -setsearchdomains Wi-Fi rollet.family
    SCRIPT
            if ! cmp -s /opt/homebrew/etc/openvpn/up.sh.new /opt/homebrew/etc/openvpn/up.sh 2>/dev/null; then
              mv /opt/homebrew/etc/openvpn/up.sh.new /opt/homebrew/etc/openvpn/up.sh
              chown root:admin /opt/homebrew/etc/openvpn/up.sh
              chmod 750 /opt/homebrew/etc/openvpn/up.sh
            else
              rm /opt/homebrew/etc/openvpn/up.sh.new
            fi

            cat > /opt/homebrew/etc/openvpn/down.sh.new << 'SCRIPT'
    #!/bin/sh
    /usr/sbin/networksetup -setdnsservers Wi-Fi Empty
    /usr/sbin/networksetup -setsearchdomains Wi-Fi Empty
    SCRIPT
            if ! cmp -s /opt/homebrew/etc/openvpn/down.sh.new /opt/homebrew/etc/openvpn/down.sh 2>/dev/null; then
              mv /opt/homebrew/etc/openvpn/down.sh.new /opt/homebrew/etc/openvpn/down.sh
              chown root:admin /opt/homebrew/etc/openvpn/down.sh
              chmod 750 /opt/homebrew/etc/openvpn/down.sh
            else
              rm /opt/homebrew/etc/openvpn/down.sh.new
            fi

            OVPN_SRC="/Users/havoc/Library/Mobile Documents/com~apple~CloudDocs/Downloads/OpenVPN_Server___vpn_rollet_family_macbookpro.ovpn"
            if [ -f "$OVPN_SRC" ]; then
              cp "$OVPN_SRC" /opt/homebrew/etc/openvpn/openvpn.conf.new
              printf '\nup /opt/homebrew/etc/openvpn/up.sh\ndown /opt/homebrew/etc/openvpn/down.sh\nscript-security 2\n' \
                >> /opt/homebrew/etc/openvpn/openvpn.conf.new
              if ! cmp -s /opt/homebrew/etc/openvpn/openvpn.conf.new /opt/homebrew/etc/openvpn/openvpn.conf 2>/dev/null; then
                echo "OpenVPN config changed, updating and restarting service..."
                /opt/homebrew/bin/brew services stop openvpn 2>/dev/null || true
                mv /opt/homebrew/etc/openvpn/openvpn.conf.new /opt/homebrew/etc/openvpn/openvpn.conf
                chown root:admin /opt/homebrew/etc/openvpn/openvpn.conf
                chmod 640 /opt/homebrew/etc/openvpn/openvpn.conf
                /opt/homebrew/bin/brew services start openvpn 2>/dev/null || true
              else
                echo "OpenVPN config unchanged, skipping restart."
                rm /opt/homebrew/etc/openvpn/openvpn.conf.new
              fi
            else
              echo "WARNING: OpenVPN config not found in iCloud Drive, skipping update."
            fi
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

  system.defaults = {
    dock.persistent-apps = [ ];
  };
  homebrew = {
    enable = true;
    taps = [
      "dopplerhq/cli"
      "minio/stable"
      "vitobotta/tap"
    ];
    brews = [
      "dopplerhq/cli/doppler"
      "helm"
      "openvpn"
      "k9s"
      "kubectl"
      "minio/stable/mc"
      "tailscale"
      "vitobotta/tap/hetzner_k3s"
    ];
    casks = [
      "battle-net"
      "curseforge"
      "element"
      "obsidian"
      "ollama-app"
      "orion"
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
