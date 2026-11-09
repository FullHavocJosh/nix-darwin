# Helper function: Open a workspace for manual file editing with AI assistance
# Usage: _gpa_create_edit_workspace <file_path> <recommendation_text>
function _gpa_create_edit_workspace() {
  local file_path="$1"
  local recommendation="$2"
  local file_dir=$(dirname "$file_path")
  local file_name=$(basename "$file_path")
  local session_name="gpa-fix-${file_name}-$$"

  # Create a temporary file with the recommendation for aidev
  local rec_file="/tmp/gpa_recommendation_$$.txt"
  echo "$recommendation" > "$rec_file"

  local cmd_aidev="echo '=== Code Review Fix Assistant ==='; echo; echo 'Recommendation:'; cat '$rec_file'; echo; echo 'Starting aidev...'; echo; aidev --direct \"Help me implement this fix: \$(cat '$rec_file'). The file to fix is: $file_path\""

  _ai_edit_workspace "$session_name" "$file_dir" "nvim '$file_path'" "$cmd_aidev"

  echo "  Workspace: $session_name"
  echo "  File: $file_path"
  echo "  Edit the file in the new workspace, then switch back here when done."
  echo ""
}

# Helper function: Use aidev to auto-fix a file based on recommendation
# Usage: _gpa_auto_fix <file_path> <recommendation_text>
function _gpa_auto_fix() {
  local file_path="$1"
  local recommendation="$2"

  echo ""
  echo "ℹ Starting aidev to automatically fix: $file_path"
  echo ""

  # Use aidev to fix the file
  aidev -p "Fix this file based on the following recommendation. Make the necessary changes to address the issue.

File: $file_path

Recommendation:
$recommendation

Please make the changes directly to the file."

  local exit_code=$?

  if [ $exit_code -eq 0 ]; then
    # Re-stage the file after aidev makes changes
    git add "$file_path"
    echo ""
    echo "✓ aidev completed. File re-staged."
    return 0
  else
    echo ""
    echo "⚠ aidev session ended. Check if changes were made."
    return 1
  fi
}

# DISABLED: Review caching functions (not reliable, disabled for now)
# 
# # Helper function: Get hash of file's staged content
# # Usage: _gpa_get_file_hash <file_path>
# function _gpa_get_file_hash() {
#   local file="$1"
#   # Hash the staged content of the file (not the file itself)
#   git diff --cached -- "$file" | shasum -a 256 | cut -d' ' -f1
# }
# 
# # Helper function: Check if a file has been reviewed and hasn't changed
# # Usage: _gpa_is_file_reviewed <file_path>
# function _gpa_is_file_reviewed() {
#   local file="$1"
#   local git_root=$(git rev-parse --show-toplevel 2>/dev/null)
#   local cache_file="$git_root/.git/gpa_review_cache"
#   
#   if [ ! -f "$cache_file" ]; then
#     return 1  # No cache file, file not reviewed
#   fi
#   
#   local current_hash=$(_gpa_get_file_hash "$file")
#   
#   # Check if this file+hash exists in cache
#   if grep -q "^${file}:${current_hash}$" "$cache_file" 2>/dev/null; then
#     return 0  # File reviewed and unchanged
#   fi
#   
#   return 1  # File not reviewed or changed
# }
# 
# # Helper function: Mark a file as reviewed
# # Usage: _gpa_mark_file_reviewed <file_path>
# function _gpa_mark_file_reviewed() {
#   local file="$1"
#   local git_root=$(git rev-parse --show-toplevel 2>/dev/null)
#   local cache_file="$git_root/.git/gpa_review_cache"
#   
#   local current_hash=$(_gpa_get_file_hash "$file")
#   
#   # Create cache file if it doesn't exist
#   touch "$cache_file"
#   
#   # Remove any existing entries for this file (in case hash changed)
#   grep -v "^${file}:" "$cache_file" > "${cache_file}.tmp" 2>/dev/null || true
#   mv "${cache_file}.tmp" "$cache_file"
#   
#   # Add new entry
#   echo "${file}:${current_hash}" >> "$cache_file"
# }

