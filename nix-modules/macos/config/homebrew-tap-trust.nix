{ config, lib, ... }:
{
  # Prepend tap trust setup to system.checks so it runs BEFORE brew bundle. cleanup = "check" runs
  # brew bundle cleanup from system.checks, ahead of activationScripts.homebrew, and fails on any
  # untrusted tap when ~/.homebrew/trust.json is missing.
  system.checks.text = lib.mkBefore ''
        USER_HOME=$(eval echo ~${config.system.primaryUser})
        TRUST_FILE="$USER_HOME/.homebrew/trust.json"
        mkdir -p "$USER_HOME/.homebrew"
        /usr/bin/python3 -c "
    import json, os
    tf = '$TRUST_FILE'
    taps = 'dopplerhq/cli gcenx/wine minio/stable music-assistant/tap nikitabobko/tap sableclient/sable slima4/claude-tui vitobotta/tap warrensbox/tap xykong/tap'.split()
    try:
        with open(tf) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d['trustedtaps'] = sorted(set(d.get('trustedtaps', []) + taps))
    with open(tf, 'w') as f:
        json.dump(d, f, indent=2)
        f.write('\n')
    "
        chown ${config.system.primaryUser} "$TRUST_FILE"
  '';
}
