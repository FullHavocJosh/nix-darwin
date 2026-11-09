# Usage: _gpa_review_batch_with_timeout <batch> <batch_num> <total_batches> [tier_override]
# Returns: JSON array of issues or empty array on failure
function _gpa_review_batch_with_timeout() {
  local batch="$1"
  local batch_num="$2"
  local total_batches="$3"
  local tier_override="${4:-auto}"  # Optional tier override

  # Local model (qwen3.5-9b via aider on llama.cpp): a review batch can take several minutes, mostly generation
  # at 10-22 tok/s (see _local_llm_timeout in .zshrc_functions_ai for the numbers), so the local limit is
  # AI_LOCAL_REVIEW_TIMEOUT (default 900s). It must not be lower than the aider call's own limit or this outer
  # watchdog kills a review that is still working. Claude Code (--tier): one call is capped at GPA_CLAUDE_TIMEOUT
  # (default 180s) inside _run_ai_direct_claude, so the watchdog allows a little more.
  local timeout max_retries
  if [[ "$tier_override" == "auto" ]]; then
    timeout=$(_local_llm_timeout review)
    max_retries=2
  else
    timeout=$(( ${GPA_CLAUDE_TIMEOUT:-180} + 30 ))
    max_retries=2
  fi
  local retry_count=0
  
  while [ $retry_count -lt $max_retries ]; do
    if [ $retry_count -gt 0 ]; then
      echo "  ⚠ Retry attempt $retry_count of $max_retries..." >&2
    fi
    
    # Create a temporary file to store the result
    local tmp_result=$(mktemp)
    local tmp_pid_file=$(mktemp)
    
    # Run the review in a background process.
    # Redirect subshell stdout+stderr to /dev/null: the result travels through
    # $tmp_result (explicit redirect), so inherited fds are not needed. This also
    # prevents any streaming text from claude from leaking to the terminal.
    (
      local result=$(_gpa_review_batch "$batch" "$batch_num" "$total_batches" "$tier_override" 2>/dev/null)
      echo "$result" > "$tmp_result"
    ) >/dev/null 2>/dev/null &
    
    local bg_pid=$!
    echo $bg_pid > "$tmp_pid_file"
    
    # Wait for the process with timeout and show progress
    local elapsed=0
    local interval=0.5
    local spinner_chars="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    local spinner_idx=0
    local tick_count=0
    
    # Print initial status on same line
    printf "  " >&2
    
    while kill -0 $bg_pid 2>/dev/null; do
      # Update elapsed time every 2 ticks (1 second)
      if [ $((tick_count % 2)) -eq 0 ]; then
        elapsed=$((tick_count / 2))
      fi
      
      if [ $elapsed -ge $timeout ]; then
        printf "\r  ⚠ AI review timed out after ${timeout} seconds\n" >&2
        kill -9 $bg_pid 2>/dev/null
        wait $bg_pid 2>/dev/null
        rm -f "$tmp_result" "$tmp_pid_file"
        ((retry_count++))
        break
      fi
      
      # Show spinner and elapsed time
      local spinner_char="${spinner_chars:$spinner_idx:1}"
      printf "\r  %s Analyzing code... %ds elapsed" "$spinner_char" "$elapsed" >&2
      
      sleep $interval
      ((tick_count++))
      ((spinner_idx = (spinner_idx + 1) % ${#spinner_chars}))
    done
    
    # Clear the progress line if process completed successfully
    if [ $elapsed -lt $timeout ]; then
      printf "\r  ✓ Analysis complete (%ds)        \n" "$elapsed" >&2
    fi
    
    # Check if we broke out due to timeout
    if [ $elapsed -ge $timeout ]; then
      continue
    fi
    
    # Wait for background process to complete
    wait $bg_pid
    local exit_code=$?
    
    # Read the result
    local batch_result=""
    if [ -f "$tmp_result" ]; then
      batch_result=$(cat "$tmp_result")
      rm -f "$tmp_result"
    fi
    rm -f "$tmp_pid_file"
    
    # Validate the result
    if [ $exit_code -eq 0 ] && [ -n "$batch_result" ]; then
      # Try to validate as JSON
      if echo "$batch_result" | jq empty 2>/dev/null; then
        echo "$batch_result"
        return 0
      else
        # Extract last JSON array: greedy .* before forces rightmost match,
        # lazy .*? inside captures minimal content to avoid crossing array boundaries.
        local extracted_json=$(echo "$batch_result" | perl -0777 -pe 's/.*(\[.*?\])\s*$/$1/s' | head -c 50000)
        
        if [ -n "$extracted_json" ] && echo "$extracted_json" | jq empty 2>/dev/null; then
          echo "$extracted_json"
          return 0
        fi
        
        # Soft failure - could not parse
        printf "\r  ⚠ Could not parse response as JSON\n" >&2
        echo "[]"
        return 2
      fi
    elif [ $exit_code -eq 2 ]; then
      # Soft failure from _gpa_review_batch (unparseable)
      echo "$batch_result"
      return 2
    fi
    
    # Failed, increment retry
    ((retry_count++))
  done
  
  # All retries failed
  echo "  ✗ AI review failed after $max_retries attempts" >&2
  return 1
}

