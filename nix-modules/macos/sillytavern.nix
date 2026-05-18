{ ... }:
let
  sillyTavernConfig = ''
    {
      "listen": true,
      "whitelistMode": false,
      "whitelistIPs": [],
      "basicAuthMode": false,
      "enableCorsProxy": false,
      "securityOverride": true
    }
  '';
in
{
  system.activationScripts.sillytavern.text = ''
    STDIR="/Users/havoc/SillyTavern"
    GIT="/opt/homebrew/bin/git"
    NPM="/opt/homebrew/bin/npm"
    if [ ! -d "$STDIR" ]; then
      echo "Cloning SillyTavern..."
      sudo -u havoc "$GIT" clone --branch release https://github.com/SillyTavern/SillyTavern "$STDIR"
      sudo -u havoc sh -c "cd '$STDIR' && '$NPM' ci --production"
    else
      echo "Updating SillyTavern..."
      sudo -u havoc sh -c "cd '$STDIR' && '$GIT' pull && '$NPM' ci --production"
    fi

    # Configure SillyTavern for network access with security override
    # Note: securityOverride is required when listen=true without auth/whitelist
    CONFIG_FILE="$STDIR/config.yaml"
    if ! grep -q "securityOverride: true" "$CONFIG_FILE" 2>/dev/null; then
      echo "Updating SillyTavern network configuration..."
      # Use sed to update the existing config.yaml
      sudo -u havoc /usr/bin/sed -i "" "s/securityOverride: false/securityOverride: true/" "$CONFIG_FILE"
    fi
  '';

  # Service disabled -- installation/update scripts above are kept intact.
  # Uncomment to re-enable the launchd agent:
  # launchd.user.agents.sillytavern = {
  #   serviceConfig = {
  #     ProgramArguments = [
  #       "/opt/homebrew/opt/node@22/bin/node"
  #       "/Users/havoc/SillyTavern/server.js"
  #     ];
  #     WorkingDirectory = "/Users/havoc/SillyTavern";
  #     KeepAlive = true;
  #     RunAtLoad = true;
  #     StandardOutPath = "/tmp/sillytavern.log";
  #     StandardErrorPath = "/tmp/sillytavern.error.log";
  #     LimitLoadToSessionType = [
  #       "Aqua"
  #       "Background"
  #     ];
  #   };
  # };
}
