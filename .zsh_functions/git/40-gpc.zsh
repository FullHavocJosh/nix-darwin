function gpc() {
  # Usage: gpc [-m|--message "<subject>"] [-d|--description "<body>"]
  # With -m the commit message is yours: no AI provider is called and nothing prompts (the same message can come in
  # through AI_COMMIT_MESSAGE / AI_COMMIT_BODY, which is how `gpa -m` hands it down).
  # Without -m the message comes from the local model (llama.cpp through aider); no cloud model is called.
  local AI_COMMIT_MESSAGE="${AI_COMMIT_MESSAGE:-}" AI_COMMIT_BODY="${AI_COMMIT_BODY:-}"
  while (( $# )); do
    case "$1" in
      -m|--message) AI_COMMIT_MESSAGE="$2"; shift 2 ;;
      -d|--description|--body) AI_COMMIT_BODY="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  # Validate git repository
  _check_git_repo || return 1

  # Check if there are staged changes
  if ! git diff --cached --quiet; then
    if [[ -n "$AI_COMMIT_MESSAGE" ]]; then
      _gpc_commit_push "$AI_COMMIT_MESSAGE" "$AI_COMMIT_BODY"
      return $?
    fi
    echo ""
    echo "⚪ llama.cpp | $(_llamacpp_model_short) — Generating commit message..."
    # Get the diff of staged changes
    local diff_output=$(git diff --cached)
    
    # Debug: Show diff size
    local diff_lines=$(echo "$diff_output" | wc -l | tr -d ' ')
    local diff_chars=$(echo "$diff_output" | wc -c | tr -d ' ')
    echo "  Diff size: $diff_lines lines, $diff_chars characters"

    # Retry loop for AI commit message generation
    local max_retries=3
    local retry_count=0
    local commit_msg=""
    local generation_succeeded=false
    
    while [ $retry_count -lt $max_retries ]; do
      local ai_output=$(echo "Review the following git diff and generate a concise, single-sentence commit message that describes the changes. The message should be in imperative mood (e.g., 'Add feature' not 'Added feature'). Maximum 72 characters. Return ONLY the commit message, nothing else.\n\n$diff_output" | _run_ai_plain 2>&1)
      local ai_exit=$?
      
      # Check if AI command succeeded
      if [ $ai_exit -ne 0 ]; then
        local error_msg="AI command failed (exit code: $ai_exit)"
        if echo "$ai_output" | grep -qi "timeout"; then
          error_msg="AI request timed out"
        elif echo "$ai_output" | grep -qi "API\|network\|connection"; then
          error_msg="Network or API error"
        fi
        
        # Prompt user for action
        _prompt_ai_error_action "$error_msg" "Commit message generation"
        local action=$?
        
        case $action in
          0)  # Retry
            ((retry_count++))
            if [ $retry_count -lt $max_retries ]; then
              echo "  ⟳ Retrying... (attempt $((retry_count + 1))/$max_retries)" >&2
            fi
            continue
            ;;
          1)  # Continue (skip AI, use manual)
            echo "" >&2
            echo "ℹ Skipping AI generation. Please enter commit message manually:" >&2
            read -r commit_msg
            if [ -n "$commit_msg" ]; then
              generation_succeeded=true
              break
            else
              echo "✗ Empty commit message, aborting" >&2
              return 1
            fi
            ;;
          2)  # Cancel
            echo "✗ Operation cancelled by user" >&2
            return 1
            ;;
        esac
        continue
      fi
      
      # Clean ANSI codes and OpenCode prompts for error checking
      local ai_output_clean=$(_clean_opencode_output "$ai_output")
      
      # Debug output if DEBUG_GPC is set
      if [[ -n "$DEBUG_GPC" ]]; then
        echo "" >&2
        echo "=== DEBUG: Raw AI Output ===" >&2
        echo "$ai_output" | head -10 >&2
        echo "=== DEBUG: Cleaned Output ===" >&2
        echo "$ai_output_clean" | head -10 >&2
        echo "===========================" >&2
        echo "" >&2
      fi
      
      # Check if output contains error messages (case-insensitive)
      if echo "$ai_output_clean" | grep -qi "^Error:"; then
        # Show the error and whatever follows it (e.g. a pretty-printed JSON
        # body) — grep -i "^Error:" alone only matches that one line and
        # silently drops the actual message/ref that explains the failure.
        local error_preview=$(echo "$ai_output_clean" | sed -n '/^Error:/,$p' | head -10)
        _prompt_ai_error_action "AI returned error message: $error_preview" "Commit message generation"
        local action=$?
        
        case $action in
          0)  # Retry
            ((retry_count++))
            if [ $retry_count -lt $max_retries ]; then
              echo "  ⟳ Retrying... (attempt $((retry_count + 1))/$max_retries)" >&2
            fi
            continue
            ;;
          1)  # Continue with manual input
            echo "" >&2
            echo "ℹ Skipping AI generation. Please enter commit message manually:" >&2
            read -r commit_msg
            if [ -n "$commit_msg" ]; then
              generation_succeeded=true
              break
            else
              echo "✗ Empty commit message, aborting" >&2
              return 1
            fi
            ;;
          2)  # Cancel
            echo "✗ Operation cancelled by user" >&2
            return 1
            ;;
        esac
        continue
      fi
      
      # Extract last non-empty line as commit message (use cleaned output)
      commit_msg=$(echo "$ai_output_clean" | grep -v '^$' | tail -1)

      # Check if we got a valid response
      if [ -z "$commit_msg" ]; then
        _prompt_ai_error_action "AI returned empty response" "Commit message generation"
        local action=$?
        
        case $action in
          0)  # Retry
            ((retry_count++))
            if [ $retry_count -lt $max_retries ]; then
              echo "  ⟳ Retrying... (attempt $((retry_count + 1))/$max_retries)" >&2
            fi
            continue
            ;;
          1)  # Continue with manual input
            echo "" >&2
            echo "ℹ Skipping AI generation. Please enter commit message manually:" >&2
            read -r commit_msg
            if [ -n "$commit_msg" ]; then
              generation_succeeded=true
              break
            else
              echo "✗ Empty commit message, aborting" >&2
              return 1
            fi
            ;;
          2)  # Cancel
            echo "✗ Operation cancelled by user" >&2
            return 1
            ;;
        esac
        continue
      fi
      
      # Final check if response looks like an error message (only match at start of string)
      if [[ "$commit_msg" == Error:* ]] || [[ "$commit_msg" == Debug:* ]]; then
        _prompt_ai_error_action "AI response contains error markers" "Commit message generation"
        local action=$?
        
        case $action in
          0)  # Retry
            ((retry_count++))
            if [ $retry_count -lt $max_retries ]; then
              echo "  ⟳ Retrying... (attempt $((retry_count + 1))/$max_retries)" >&2
            fi
            continue
            ;;
          1)  # Continue with manual input
            echo "" >&2
            echo "ℹ Skipping AI generation. Please enter commit message manually:" >&2
            read -r commit_msg
            if [ -n "$commit_msg" ]; then
              generation_succeeded=true
              break
            else
              echo "✗ Empty commit message, aborting" >&2
              return 1
            fi
            ;;
          2)  # Cancel
            echo "✗ Operation cancelled by user" >&2
            return 1
            ;;
        esac
        continue
      fi
      
      # Success!
      generation_succeeded=true
      break
    done
    
    # Check if we exhausted retries
    if [ "$generation_succeeded" != true ]; then
      echo "" >&2
      echo "✗ Failed to generate commit message after $max_retries attempts" >&2
      return 1
    fi

    commit_msg=$(_strip_agent_attribution "$commit_msg")
    if [[ -z "$commit_msg" ]]; then
      echo "✗ Generated commit message was only agent attribution; nothing left to commit with" >&2
      return 1
    fi

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  $commit_msg"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    # Commit with the generated message
    git commit -m "$commit_msg"

    if [ $? -eq 0 ]; then
      echo ""
      local remote_url=$(git remote get-url origin 2>/dev/null || echo "remote")
      echo "ℹ Pushing to $remote_url..."
      git push
      if [ $? -eq 0 ]; then
        echo "✓ Successfully pushed"
      else
        echo "✗ Push failed"
        return 1
      fi
    else
      echo "✗ Commit failed, skipping push"
      return 1
    fi
  else
    echo "⚠ No staged changes to commit"
    return 1
  fi
}
# Kept so the name still works: gpc only ever uses the local model now, so this is plain gpc.
function gpc-local() {
  gpc "$@"
}


