{ ... }:
{
  # Expose Homebrew and standard paths to GUI apps (e.g. Neovide finding nvim).
  # Must run as a user LaunchAgent so launchctl setenv applies to the user GUI session,
  # not the system domain (root's launchctl doesn't reach Finder-launched apps).
  launchd.user.agents.set-gui-path = {
    serviceConfig = {
      Label = "org.nixos.set-gui-path";
      ProgramArguments = [
        "/bin/sh"
        "-c"
        "/bin/launchctl setenv PATH /opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
      ];
      RunAtLoad = true;
    };
  };
}
