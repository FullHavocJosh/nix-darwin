    # tuios, the daily stack.
    #
    # Update: brew bundle's --upgrade sweep (homebrew.onActivation.upgrade, packages-tui.nix) can replace tuios
    # under a running daemon, which keeps running the build it started with. The tuios restart-server
    # stops every program in every pane (each session comes back with its layout, history and
    # fresh shells, and dev relaunches nvim), so activation only says when the daemon runs an older build. The
    # daemon's build is the Cellar directory of its executable (lsof), the installed one the Cellar directory that
    # `tuios` on PATH resolves to. The config needs nothing: tuios watches config.toml, a stow symlink into this repo.
    #
    # Panes: every pane keeps the zsh it started with, so a function or alias change from this rebuild is invisible
    # to it, and so is a new environment.variables entry: /etc/zshenv sets the environment once per shell
    # (__NIX_DARWIN_SET_ENVIRONMENT_DONE), and `source ~/.zshrc` alone does not touch it. Each pane gets the
    # set-environment script and ~/.zshrc sourced. A pane running a program gets Ctrl-Z (0x1a) first and `fg` after,
    # once its shell is back in the foreground; a program that never yields (some disable SIGTSTP) is left alone.
    # Ctrl-U (0x15) first clears a half-typed command line, so the source line never runs glued onto it. Skipped:
    # agents that are working (mid-stream) or waiting on a prompt (tuios's rule: never type into needs_input), ssh
    # and mosh panes (the Ctrl-Z would reach the remote job), and the pane running this darwin-rebuild.
    # Panes whose foreground group holds more than one process are skipped (they are agent panes with wrapper scripts).
    if command -v tuios &>/dev/null; then
      # The daemon's pid file (pgrep does not list the daemon process on macOS).
      tuios_daemon=$(cat "/tmp/tuios-$(id -u)/tuios.sock.pid" 2>/dev/null)
      if [ -n "$tuios_daemon" ] && kill -0 "$tuios_daemon" 2>/dev/null; then
        tuios_running=$(lsof -p "$tuios_daemon" -a -d txt -Fn 2>/dev/null | grep -m1 -o 'Cellar/tuios/[^/]*' | cut -d/ -f3)
        tuios_installed=$(readlink -f "$(command -v tuios)" | grep -o 'Cellar/tuios/[^/]*' | cut -d/ -f3)
        if [ -n "$tuios_running" ] && [ -n "$tuios_installed" ] && [ "$tuios_running" != "$tuios_installed" ]; then
          echo "tuios updated ($tuios_running -> $tuios_installed); the daemon still runs $tuios_running."
          echo "  Run 'tuios restart-server' when the panes can stop: it restarts every program in every pane."
        fi

        echo "Refreshing tuios panes with latest dotfiles and env vars..."
        tuios_clear=$'\x15'
        tuios_source='set_env=$(grep -o "/nix/store/[^[:space:]]*-set-environment" /etc/zshenv 2>/dev/null); [ -n "$set_env" ] && source "$set_env"; source ~/.zshrc'
        tuios ls --json 2>/dev/null | jq -r '.[].name' | while read -r tuios_session; do
          tuios list-windows -s "$tuios_session" --json </dev/null 2>/dev/null |
            jq -r '.windows[] | select(.agent_state != "working" and .agent_state != "needs_input") | "\(.window_id) \(.pid) \(.tty)"' |
            while read -r wid shell_pid tty; do
              tty=$(basename "$tty")
              fg=$(ps -o pid=,stat=,command= -t "$tty" 2>/dev/null | awk '$2 ~ /\+/')
              [ -n "$fg" ] || continue
              case "$fg" in
                *darwin-rebuild*) continue ;;
              esac
              # Skip panes whose window pid is a wrapper script (agent panes with child processes)
              fg_count=$(echo "$fg" | wc -l)
              if [ "$fg_count" -gt 1 ]; then
                continue
              fi
              case "$(echo "$fg" | awk 'NR==1 {print $3}' | xargs basename 2>/dev/null)" in
                ssh | mosh | mosh-client) continue ;;
              esac
              had_job=false
              if ! echo "$fg" | awk '{print $1}' | grep -qx "$shell_pid"; then
                had_job=true
                tuios send-text -s "$tuios_session" -w "$wid" $'\x1a' </dev/null >/dev/null 2>&1
                settled=false
                for _ in 1 2 3 4 5 6 7 8 9 10; do
                  sleep 0.3
                  if ps -o pid=,stat= -t "$tty" 2>/dev/null | awk '$2 ~ /\+/ {print $1}' | grep -qx "$shell_pid"; then
                    settled=true
                    break
                  fi
                done
                if [ "$settled" != true ]; then
                  echo "tuios pane $wid ($tuios_session) did not yield its shell after Ctrl-Z, leaving it alone"
                  continue
                fi
              fi
              tuios send-text -s "$tuios_session" -w "$wid" "$tuios_clear$tuios_source"$'\n' </dev/null >/dev/null 2>&1 ||
                echo "Failed to refresh tuios pane $wid ($tuios_session)"
              if [ "$had_job" = true ]; then
                tuios send-text -s "$tuios_session" -w "$wid" $'fg\n' </dev/null >/dev/null 2>&1 ||
                  echo "Failed to resume the foreground job in tuios pane $wid ($tuios_session)"
              fi
            done
        done
      fi
    fi
