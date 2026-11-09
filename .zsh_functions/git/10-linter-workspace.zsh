# gpa's manual-fix workspace (tuios).
_ai_edit_workspace() {
  _tuios_ai_edit_workspace "$@"
}

# Helper function: Open a workspace (nvim + aidev tabs) for linting fixes
# Usage: _linter_create_edit_workspace <files_with_issues> <lint_report>
function _linter_create_edit_workspace() {
  local -a files_array
  IFS=$'\n' read -rd '' -A files_array <<< "$1"
  local lint_report="$2"

  # Get absolute path to repo root
  local repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

  # Save the prompt to a temp file to avoid quoting issues
  local prompt_file="/tmp/lint_prompt_$$.txt"
  cat > "$prompt_file" <<EOF
Help me fix the following linting issues. The files are already open in the editor above.

Linting Issues:
$(echo -e "$lint_report")

Files to fix: ${files_array[@]}

Please review the issues and suggest fixes. I can make the changes in the editor above or you can help automate the fixes.
EOF

  # Open first file with issues in nvim
  local first_file="${files_array[1]}"
  # If file path is relative, make it absolute from repo root
  if [[ ! "$first_file" = /* ]]; then
    first_file="$repo_root/$first_file"
  fi

  local session_name="lint-fix-$$"
  local cmd_aidev="echo '=== aidev Linting Assistant ==='; echo; aidev --direct \"\$(cat '$prompt_file')\""

  _ai_edit_workspace "$session_name" "$repo_root" "nvim '$first_file'" "$cmd_aidev"

  echo "  Workspace: $session_name"
  echo "  Files: ${files_array[@]}"
  echo "  Edit the files in the new workspace, then switch back here when done."
  echo ""
}

