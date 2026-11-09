# Secrets: ~/.zshrc_envvars (git-ignored, chmod 600)
# Non-sensitive config: ~/.zshrc_envvars_insecure (tracked by git)

# Helper function: Clean OpenCode CLI output by removing ANSI codes and prompts
# Usage: _clean_opencode_output <output>
function _clean_opencode_output() {
  local output="$1"
  # Strip ANSI escape codes (use perl for better escape sequence handling)
  output=$(echo "$output" | perl -pe 's/\e\[[0-9;]*m//g')
  # Remove OpenCode CLI prompt lines (e.g., "> build · claude-haiku-4.5")
  # and extract only content lines (non-empty, non-prompt)
  output=$(echo "$output" | grep -v '^> ' | grep -v '^[[:space:]]*$')
  echo "$output"
}

# Read a single keypress into the named variable.
# After ESC, drains any buffered ANSI escape-sequence tail (e.g. ESC [ from
# arrow keys) so the next read is not poisoned by leftover bytes.
function _read_key() {
  # Reads one keypress into the global _KEY.
  # If ESC is pressed, drains any buffered ANSI tail bytes (e.g. ESC [ from
  # arrow keys) so subsequent reads are not poisoned by leftover input.
  read -k1 _KEY
  if [[ "$_KEY" == $'\e' ]]; then
    local _drain
    read -k10 -t 0.1 _drain 2>/dev/null || true
  fi
}

