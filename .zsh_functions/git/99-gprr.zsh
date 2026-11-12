# Git PR Ready - Rewrite the PR body, mark the PR ready, and watch it.
#
# Run it in the PR's worktree or checkout. gprr hands the work to
# ~/.config/aistack-tuios/gprr.py: it rewrites the detailed PR task list into a
# short human-readable description with the on-device 9B, marks the PR ready for
# review, and monitors it for failed checks and Qodo, Copilot and Akkido comments.
#   gprr [--monitor] [--seconds N] [--no-monitor]
# Exit codes (passed through from gprr.py):
#   0  PR clean
#   1  a check failed (also: gh or python3 missing, or no open PR on this branch)
#   2  open review feedback
#   3  still pending: run gprr again
function gprr() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "✗ gprr: gh not found" >&2
    return 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "✗ gprr: python3 not found" >&2
    return 1
  fi
  if ! gh pr view >/dev/null 2>&1; then
    echo "✗ gprr: no open PR for the current branch (run it in the PR's worktree)" >&2
    return 1
  fi
  PATH=/opt/homebrew/bin:$PATH python3 "$HOME/.config/aistack-tuios/gprr.py" "$@"
}
