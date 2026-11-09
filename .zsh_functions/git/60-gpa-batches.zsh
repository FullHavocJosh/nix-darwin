# Helper function: Split staged files into batches for AI review
# Returns batches as a JSON array where each batch is an array of file paths
# Batches are sized to keep diff output around 300 lines per batch
# Usage: _gpa_create_batches
function _gpa_create_batches() {
  local target_lines=300
  local batches="[]"
  local current_batch="[]"
  local current_batch_lines=0
  
  # Get all staged files
  local staged_files=()
  
  while IFS= read -r file; do
    staged_files+=("$file")
  done < <(git diff --cached --name-only)
  
  if [ ${#staged_files[@]} -eq 0 ]; then
    echo "[]"
    return 0
  fi
  
  # Process each file and group into batches
  for file in "${staged_files[@]}"; do
    # Get line count for this file's diff
    local file_diff_lines=$(git diff --cached -- "$file" | wc -l)
    
    # If adding this file would exceed target, start a new batch
    # (unless current batch is empty - always include at least one file per batch)
    if [ $current_batch_lines -gt 0 ] && [ $((current_batch_lines + file_diff_lines)) -gt $target_lines ]; then
      # Save current batch and start a new one
      batches=$(echo "$batches" | jq --argjson batch "$current_batch" '. += [$batch]')
      current_batch="[]"
      current_batch_lines=0
    fi
    
    # Add file to current batch
    current_batch=$(echo "$current_batch" | jq --arg file "$file" '. += [$file]')
    current_batch_lines=$((current_batch_lines + file_diff_lines))
  done
  
  # Add the last batch if it's not empty
  if [ "$(echo "$current_batch" | jq 'length')" -gt 0 ]; then
    batches=$(echo "$batches" | jq --argjson batch "$current_batch" '. += [$batch]')
  fi
  
  echo "$batches"
}

# Helper function: Check if issues warrant escalation to Opus
# Usage: _gpa_should_escalate <issues_json>
# Returns: 0 (true) if escalation recommended, 1 (false) otherwise
function _gpa_should_escalate() {
  local issues_json="$1"
  
  # Check if we have any issues at all
  local issue_count=$(echo "$issues_json" | jq 'length' 2>/dev/null)
  if [[ -z "$issue_count" ]] || [[ "$issue_count" -eq 0 ]]; then
    return 1  # No issues, no escalation
  fi
  
  # Keywords that indicate security-critical issues
  local security_keywords=("security" "credential" "secret" "password" "token" "key" "auth" "vulnerability" "injection" "xss" "csrf" "encryption")
  
  # Check for Critical severity issues with security keywords
  local has_critical_security=false
  while IFS= read -r issue_text; do
    # Check if this is a Critical issue
    local severity=$(echo "$issue_text" | jq -r '.severity' 2>/dev/null)
    if [[ "$severity" != "Critical" ]]; then
      continue
    fi
    
    # Check if issue or recommendation contains security keywords
    local issue_desc=$(echo "$issue_text" | jq -r '.issue + " " + .recommendation' 2>/dev/null | tr '[:upper:]' '[:lower:]')
    
    for keyword in "${security_keywords[@]}"; do
      if echo "$issue_desc" | grep -qi "$keyword"; then
        return 0  # Found Critical + security keyword = escalate
      fi
    done
  done < <(echo "$issues_json" | jq -c '.[]' 2>/dev/null)
  
  return 1  # No critical security issues found
}

