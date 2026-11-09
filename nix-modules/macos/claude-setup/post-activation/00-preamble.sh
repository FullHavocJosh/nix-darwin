    # This whole block runs as root (nix-darwin activation always does),
    # so `id -un` here returns "root", not the real login user -- that
    # made `sudo -u "$USER_NAME"` a no-op (already root) and left $HOME
    # as /var/root for everything below, e.g. token-savior's venv landed
    # at /var/root/bench (using macOS's ancient system python3, whose old
    # pip couldn't even resolve the package) instead of ~/bench. Use the
    # module's own username argument instead, same as config.nix does via
    # config.system.primaryUser. --set-home makes sudo actually reset
    # $HOME for the target user; without it, sudo -u alone does not.
    USER_NAME=@usernameQuoted@
    USER_HOME=$(eval echo "~$USER_NAME")

    sudo --set-home -u "$USER_NAME" bash <<'USERSCRIPT'
