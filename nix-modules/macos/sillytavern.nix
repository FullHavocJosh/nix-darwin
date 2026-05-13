{ ... }:
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
  '';

  launchd.user.agents.sillytavern = {
    serviceConfig = {
      ProgramArguments = [
        "/opt/homebrew/bin/node"
        "/Users/havoc/SillyTavern/server.js"
      ];
      WorkingDirectory = "/Users/havoc/SillyTavern";
      KeepAlive = true;
      RunAtLoad = true;
      StandardOutPath = "/tmp/sillytavern.log";
      StandardErrorPath = "/tmp/sillytavern.error.log";
      LimitLoadToSessionType = [
        "Aqua"
        "Background"
      ];
    };
  };
}
