# Helper function: Get hash of file's staged content
# Usage: _gpa_get_file_hash <file_path>
function _gpa_get_file_hash() {
  local file="$1"
  git diff --cached -- "$file" | shasum -a 256 | cut -d' ' -f1
}

# Helper function: Check if a file has been reviewed and hasn't changed
# Usage: _gpa_is_file_reviewed <file_path>
function _gpa_is_file_reviewed() {
  local file="$1"
  local git_root=$(git rev-parse --show-toplevel 2>/dev/null)
  local cache_file="$git_root/.git/gpa_review_cache"
  
  if [ ! -f "$cache_file" ]; then
    return 1  # No cache file, file not reviewed
  fi
  
  local current_hash=$(_gpa_get_file_hash "$file")
  
  # Check if this file+hash exists in cache
  if grep -q "^${file}:${current_hash}$" "$cache_file" 2>/dev/null; then
    return 0  # File reviewed and unchanged
  fi
  
  return 1  # File not reviewed or changed
}

# Helper function: Mark a file as reviewed
# Usage: _gpa_mark_file_reviewed <file_path>
function _gpa_mark_file_reviewed() {
  local file="$1"
  local git_root=$(git rev-parse --show-toplevel 2>/dev/null)
  local cache_file="$git_root/.git/gpa_review_cache"
  
  local current_hash=$(_gpa_get_file_hash "$file")
  
  # Remove any old entries for this file
  if [ -f "$cache_file" ]; then
    grep -v "^${file}:" "$cache_file" > "${cache_file}.tmp" 2>/dev/null || touch "${cache_file}.tmp"
    mv "${cache_file}.tmp" "$cache_file"
  fi
  
  # Add new entry
  echo "${file}:${current_hash}" >> "$cache_file"
}

# Helper function: Clear review cache
# Usage: _gpa_clear_cache
function _gpa_clear_cache() {
  local git_root=$(git rev-parse --show-toplevel 2>/dev/null)
  local cache_file="$git_root/.git/gpa_review_cache"
  
  if [ -f "$cache_file" ]; then
    rm -f "$cache_file"
    echo "✓ Review cache cleared"
  else
    echo "ℹ No review cache to clear"
  fi
}

