# =============================================================================
# Git Workflow Functions
# Helper functions and main workflow commands for git operations
# =============================================================================

# Helper function: Launch a script in a new terminal window (macOS)
# Usage: _launch_terminal_window <script_path> <label>
# Returns 0 on success, 1 if no terminal could be found
function _launch_terminal_window() {
  local script="$1"
  local label="${2:-terminal window}"

  if [[ "$OSTYPE" == darwin* ]] || [[ "$(uname 2>/dev/null)" == "Darwin" ]]; then
    # Prefer the terminal we're already running in
    case "$TERM_PROGRAM" in
      ghostty)
        if command -v ghostty &>/dev/null; then
          nohup ghostty -e "$script" >/dev/null 2>&1 &
          echo "✓ Launched $label in new Ghostty window"
          return 0
        fi
        ;;
      iTerm.app)
        osascript -e "tell application \"iTerm2\" to create window with default profile command \"$script\"" >/dev/null 2>&1
        echo "✓ Launched $label in new iTerm2 window"
        return 0
        ;;
    esac
    # Fallbacks: wezterm, then Terminal.app (always present)
    if command -v wezterm &>/dev/null; then
      nohup wezterm start -- "$script" >/dev/null 2>&1 &
    else
      open -a Terminal "$script"
    fi
    echo "✓ Launched $label in new terminal window"
    return 0
  fi

  # This should not happen in macOS
  return 1
}

# Helper function: Check if current directory is a git repository
function _check_git_repo() {
  if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "✗ Error: Not in a git repository"
    return 1
  fi
  return 0
}



