function _gpa_impl() {
  # Git Partial Add with AI code review
  # Usage: gpa [--tier=haiku|sonnet|opus] [--auto]
  #
  # Reviews run on the local model (llama.cpp through aider). --tier=<model> reviews with that Claude Code model
  # instead (billed); Claude Code sonnet is also the fallback when the local model fails and the escalation target
  # for Critical security findings, both suppressed under AI_LOCAL_ONLY.
  #
  # --auto: non-interactive mode for AI-agent callers (e.g. Claude Code).
  # Stages all changes, auto-fixes lint issues, auto-escalates ambiguous
  # AI-review escalation prompts, and never blindly proceeds past something
  # that needs a judgment call (real secrets, AI review that fully failed).
  # If issues are found, prints them and exits non-zero instead of entering
  # the interactive fix loop or recursing into aidev — the caller is
  # expected to read the findings, fix them itself, and re-run `gpa --auto`.
  # AI_LOCAL_DEFAULT (set system-wide on hosts with a local llama-server, see
  # llamacpp-local.nix) makes plain gpa behave like gpa-local: no Claude Code
  # fallback/escalation (an explicit --tier still asks Claude Code). Guarded on AI_LOCAL_ONLY being unset so
  # gpa-local calling back into gpa here doesn't recurse. Override for one
  # call with `unset AI_LOCAL_DEFAULT` first.
  if [[ -n "$AI_LOCAL_DEFAULT" ]] && [[ -z "$AI_LOCAL_ONLY" ]]; then
    gpa-local "$@"
    return $?
  fi


  # Parse optional --tier and --auto flags
  local tier_override="auto"
  local auto_mode=false
  for arg in "$@"; do
    case $arg in
      --tier=haiku|--tier=sonnet|--tier=opus)
        tier_override="${arg#--tier=}"
        shift
        ;;
      --tier=*)
        echo "✗ Invalid tier. Use: haiku, sonnet, or opus"
        return 1
        ;;
      --auto)
        auto_mode=true
        shift
        ;;
    esac
  done


  
  # Save current shell options and disable tracing
  local prev_opts=$-
  setopt local_options
  [[ $prev_opts == *x* ]] && setopt no_xtrace

  # Validate git repository
  _check_git_repo || return 1

  # Check if there are ANY changes (staged, unstaged, or untracked)
  local has_unstaged=$(git diff --quiet; echo $?)
  local has_staged=$(git diff --cached --quiet; echo $?)
  local has_untracked=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')
  
  if [[ "$has_unstaged" -eq 0 ]] && [[ "$has_staged" -eq 0 ]] && [[ "$has_untracked" -eq 0 ]]; then
    echo "⚠ No changes to stage or review"
    return 1
  fi

  # Get git root directory for proper path resolution
  local git_root=$(git rev-parse --show-toplevel)
  local current_dir=$(pwd)
  local relative_to_root="${current_dir#$git_root}"
  relative_to_root="${relative_to_root#/}"  # Remove leading slash if present
  
  # Get list of changed files with status - properly handle filenames with spaces
  local changed_files=()
  local file_status=()
  local display_files=()  # Files as shown by git status (for display)
  local auto_excluded_files=()  # Files automatically excluded
  
  while IFS= read -r line; do
    # Parse git status --short format: XY filename
    # First 2 chars are status, then space, then filename
    local git_status="${line:0:2}"
    local file="${line:3}"
    
    # Only include unstaged changes (status code in second position)
    # Check for: modified (M), deleted (D), or untracked (??)
    if [[ "$git_status" == " M" || "$git_status" == " D" || "$git_status" == "??" ]]; then
      # Check if file should be auto-excluded
      local file_basename=$(basename "$file")
      if [[ "$file_basename" == ".terraform.lock.hcl" ]]; then
        auto_excluded_files+=("$file")
        continue
      fi
      
      # Convert path relative to current dir to path relative to git root
      local file_from_root
      if [[ -n "$relative_to_root" ]]; then
        file_from_root="${relative_to_root}/${file}"
      else
        file_from_root="$file"
      fi
      
      changed_files+=("$file_from_root")
      file_status+=("$git_status")
      display_files+=("$file")  # Keep original for display
    fi
  done < <(git status --short)
  
  # Show auto-excluded files if any
  if [ ${#auto_excluded_files[@]} -gt 0 ]; then
    echo "ℹ Auto-excluded ${#auto_excluded_files[@]} file(s):"
    for file in "${auto_excluded_files[@]}"; do
      echo "  ⊝ $file"
    done
    echo ""
  fi

  # Check if there are already staged changes
  local staged_count=$(git diff --cached --name-only | wc -l | tr -d ' ')
  
  # If there are unstaged changes, let user select what to stage
  if [ ${#changed_files[@]} -gt 0 ]; then
    if $auto_mode; then
      echo "ℹ Auto mode: staging all ${#changed_files[@]} file(s)"
      for file in "${changed_files[@]}"; do
        git -C "$git_root" add "$file" 2>/dev/null
      done
      echo "✓ Staged ${#changed_files[@]} file(s)"
    else
    # Show already-staged files if any
    if [ "$staged_count" -gt 0 ]; then
      local GREEN='\033[0;32m'
      local NC='\033[0m'
      echo "Changes to be committed:"
      git diff --cached --name-status | while IFS=$'\t' read -r file_status_code file; do
        local label=""
        case "$file_status_code" in
          M) label="modified:  " ;;
          A) label="new file:  " ;;
          D) label="deleted:   " ;;
          R) label="renamed:   " ;;
          *) label="$file_status_code         " ;;
        esac
        echo -e "  ${GREEN}${label}${file}${NC}"
      done
      echo ""
      echo "  [Enter] Continue with already-staged files"
      echo ""
    fi
    
    # Display files with numbers and status like git status
    echo "Select files to stage and review:"
    echo ""
    echo "  a) All files"
    echo ""
    local i=1
    for idx in {1..${#changed_files[@]}}; do
      local file="${display_files[$idx]}"
      local git_status="${file_status[$idx]}"
      echo "  $i) $git_status $file"
      ((i++))
    done
    echo ""
    echo "  q) Exit"
    echo ""
    
    if [ "$staged_count" -gt 0 ]; then
      echo -n "Enter numbers, 'a' for all, Enter to continue with staged, or 'q' to exit: "
    else
      echo -n "Enter numbers separated by spaces (e.g., '1 3 5'), 'a' for all, or 'q' to exit: "
    fi
    
    # Read the entire line with full readline support (backspace, arrow keys, etc.)
    local selection
    read -r selection
    
    # Check for quit command
    if [[ "$selection" == "q" ]] || [[ "$selection" == "quit" ]] || [[ "$selection" == $'\x1b'* ]]; then
      echo "✓ Cancelled"
      return 0
    fi
    
    # Check for empty input (just Enter)
    if [[ -z "$selection" ]]; then
      # Empty input (Enter key) - handle immediately
      if [ "$staged_count" -gt 0 ]; then
        echo "✓ Continuing with $staged_count already-staged file(s)"
        # Skip to the review section (set selection to empty and let flow continue)
        selection=""
      else
        echo "✗ No files are staged"
        return 1
      fi
    else
      
      # Handle selection
      case "$selection" in
        q | Q)
          echo "✓ Cancelled"
          return 0
          ;;
        a | A)
          # Stage all files - run git add from repo root to handle relative paths correctly
          echo "ℹ Staging all ${#changed_files[@]} file(s)"
          if [ ${#auto_excluded_files[@]} -gt 0 ]; then
            echo "  (excluding ${#auto_excluded_files[@]} auto-excluded file(s))"
          fi
          for file in "${changed_files[@]}"; do
            git -C "$git_root" add "$file" 2>/dev/null
          done
          echo "✓ Staged ${#changed_files[@]} file(s)"
          ;;
        *)
          # Stage selected files
          local selected_files=()
          for num in $selection; do
            if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#changed_files[@]}" ]; then
              # Note: zsh arrays are 1-indexed by default, so we use $num directly
              local selected_file="${changed_files[$num]}"
              if [ -n "$selected_file" ]; then
                selected_files+=("$selected_file")
              fi
            fi
          done

          if [ ${#selected_files[@]} -eq 0 ]; then
            echo "✗ No valid files selected"
            return 1
          fi

          # Stage each file individually - run git add from repo root to handle relative paths correctly
          echo "ℹ Staging ${#selected_files[@]} file(s)..."
          for file in "${selected_files[@]}"; do
            git -C "$git_root" add "$file" 2>/dev/null
          done
          echo "✓ Staged ${#selected_files[@]} file(s)"
          ;;
      esac
    fi
    fi
  else
    # No unstaged changes, but there are staged changes - proceed to review them
    if [ "$staged_count" -gt 0 ]; then
      local GREEN='\033[0;32m'
      local NC='\033[0m'
      echo "Changes to be committed:"
      git diff --cached --name-status | while IFS=$'\t' read -r file_status_code file; do
        local label=""
        case "$file_status_code" in
          M) label="modified:  " ;;
          A) label="new file:  " ;;
          D) label="deleted:   " ;;
          R) label="renamed:   " ;;
          *) label="$file_status_code         " ;;
        esac
        echo -e "  ${GREEN}${label}${file}${NC}"
      done
      echo ""
    fi
  fi

  # Check if there are staged changes to review
  if git diff --cached --quiet; then
    echo ""
    echo "⚠ No files are staged for review"
    return 0
  fi

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "ℹ Running secrets detection scan..."
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  # Run secrets detection using helper function
  if ! _check_for_secrets "$auto_mode"; then
    echo "✗ Secrets detection aborted commit."
    return 1
  fi

  echo "✓ No secrets detected in staged changes"

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "ℹ Running linters on staged files..."
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  # Run linters
  if ! _run_linters "$auto_mode"; then
    echo "✗ Linting check aborted."
    return 1
  fi

  # --no-review (GPA_NO_REVIEW): the caller already reviewed its own change; secrets and lint passed, so commit
  if [[ -n "${GPA_NO_REVIEW:-}" ]]; then
    echo ""
    echo "ℹ AI code review skipped (--no-review): secrets scan and linters passed"
    echo ""
    gpc
    return $?
  fi
  
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "ℹ Running AI code review on staged changes..."
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  # Create batches for review
  echo "ℹ Analyzing staged files and creating review batches..."
  local batches=$(_gpa_create_batches)
  local batch_count=$(echo "$batches" | jq 'length')
  
  if [ "$batch_count" -eq 0 ]; then
    echo ""
    echo "✓ All staged files have been previously reviewed with no changes"
    echo ""

    if $auto_mode; then
      echo "ℹ Auto mode: committing and pushing"
      echo ""
      gpc
      return $?
    fi

    echo "Options:"
    echo "  [Enter] Commit and push (gpc)"
    echo "  [r]     Re-review all files (clear cache)"
    echo "  [esc]   Cancel - keep staged"
    echo ""
    echo -n "Your choice: "
    _read_key
    echo ""

    case "$_KEY" in
      y | Y | $'\n')
        echo ""
        gpc
        return $?
        ;;
      r | R)
        echo ""
        _gpa_clear_cache
        echo ""
        echo "Re-running gpa to review all files..."
        echo ""
        gpa
        return $?
        ;;
      *)
        echo "ℹ Keeping changes staged."
        return 0
        ;;
    esac
  fi
  
  local total_files=$(git diff --cached --name-only | wc -l)
  local total_lines=$(git diff --cached | wc -l)
  
  echo "ℹ Processing $total_files file(s) in $batch_count batch(es)"
  echo "  Total changes: $total_lines lines"
  if [[ "$tier_override" == "auto" ]]; then
    echo "  Model: ⚪ llama.cpp | $(_llamacpp_model_short)"
  else
    echo "  Model: ☁ Claude Code $tier_override (--tier)"
  fi
  echo ""
  # Process each batch and collect all issues
  local all_issues="[]"
  local batch_index=0
  local failed_batches=0
  local soft_failed_batches=0  # Track unparseable responses separately
  local ai_review_failed=false
  
  while [ $batch_index -lt $batch_count ]; do
    local batch=$(echo "$batches" | jq -c ".[$batch_index]")
    local batch_num=$((batch_index + 1))
    
    local tier_icon="⚪" tier_label="$(_llamacpp_model_short)" full_model_display="llama.cpp | $(_llamacpp_model_short)"
    if [[ "$tier_override" != "auto" ]]; then
      tier_icon="☁"; tier_label="Claude $tier_override"; full_model_display="Claude Code | $tier_override"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$tier_icon $tier_label — Reviewing batch $batch_num of $batch_count... [$full_model_display]"
    
    # Review this batch with timeout and retry
    # Note: must separate local declaration from assignment to preserve exit code.
    # In zsh, `local var=$(cmd)` swallows the subshell exit code.
    local batch_issues
    batch_issues=$(_gpa_review_batch_with_timeout "$batch" "$batch_num" "$batch_count" "$tier_override")
    local review_status=$?
    
    if [ $review_status -eq 0 ]; then
      # Success - merge batch issues into all_issues
      if [ -n "$batch_issues" ] && echo "$batch_issues" | jq empty 2>/dev/null; then
        # Filter out invalid/malformed issue objects
        # Valid issues must have: file, severity, issue, recommendation fields
        local valid_batch_issues=$(echo "$batch_issues" | jq '[.[] | select(type == "object" and has("file") and has("severity") and has("issue") and has("recommendation"))]' 2>/dev/null)
        
        if [ -n "$valid_batch_issues" ]; then
          local issue_count=$(echo "$valid_batch_issues" | jq 'length')
          if [ "$issue_count" -gt 0 ]; then
            echo "  Found $issue_count issue(s) in this batch"
            
            # Escalate local Critical+security findings to Claude Code sonnet. Only for local reviews (--tier already
            # used Claude Code) and never under AI_LOCAL_ONLY (gpa-local, AI_LOCAL_DEFAULT hosts).
            local can_escalate=false
            [[ "$tier_override" == "auto" && -z "$AI_LOCAL_ONLY" ]] && can_escalate=true

            if $can_escalate && _gpa_should_escalate "$valid_batch_issues"; then
              echo ""
              echo "  ⚠ CRITICAL SECURITY ISSUE DETECTED"
              echo "  Local model found Critical+security issues."
              echo ""
              echo "  Recommendation: Re-review with Claude Code sonnet (billed) for authoritative security analysis."
              echo ""

              local escalate_choice
              if $auto_mode; then
                echo "  ℹ Auto mode: escalating to Claude Code for authoritative review"
                escalate_choice="y"
              else
                echo "  Options:"
                echo "    [y] Yes - Escalate to Claude Code (recommended)"
                echo "    [n] No  - Keep local findings"
                echo ""
                echo -n "  Your choice: "
                read -r escalate_choice
              fi

              if [[ "$escalate_choice" == "y" || "$escalate_choice" == "Y" ]]; then
                echo ""
                echo "  ☁  Escalating to Claude Code sonnet..."
                local cloud_issues=$(_gpa_review_batch_with_timeout "$batch" "$batch_num" "$batch_count" "cloud-escalation")
                local cloud_status=$?

                if [ $cloud_status -eq 0 ] && [ -n "$cloud_issues" ] && echo "$cloud_issues" | jq empty 2>/dev/null; then
                  local valid_cloud_issues=$(echo "$cloud_issues" | jq '[.[] | select(type == "object" and has("file") and has("severity") and has("issue") and has("recommendation"))]' 2>/dev/null)
                  local cloud_issue_count=$(echo "$valid_cloud_issues" | jq 'length')
                  echo "  ☁  Claude Code review complete: Found $cloud_issue_count issue(s)"
                  valid_batch_issues="$valid_cloud_issues"
                else
                  echo "  ⚠ Claude Code escalation failed, keeping local findings"
                fi
                echo ""
              fi
            fi
            all_issues=$(echo "$all_issues" | jq --argjson batch "$valid_batch_issues" '. + $batch')
          else
            echo "  ✓ No issues found in this batch"
          fi
        else
          echo "  ✓ No issues found in this batch"
          # No issues found - continue
        fi
      else
        echo "  ⚠ Batch review returned invalid JSON"
        ((failed_batches++))
      fi
    elif [ $review_status -eq 2 ]; then
      # Soft failure - unparseable response (already retried)
      echo "  ⚠ AI response could not be parsed (after retries)"
      ((soft_failed_batches++))
    else
      # Hard failure - API error, timeout, network issue
      echo "  ✗ Batch review failed completely"
      ((failed_batches++))
    fi
    
    echo ""
    ((batch_index++))
  done
  
  # Check if all batches failed (hard failures)
  if [ $failed_batches -eq $batch_count ]; then
    ai_review_failed=true
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠ WARNING: AI code review could not be completed"
    echo "  All $batch_count batch(es) failed after multiple retry attempts"
    echo ""
    echo "This could be due to:"
    echo "  - Network connectivity issues"
    echo "  - AI service unavailability"
    echo "  - Rate limiting"
    echo ""

    if $auto_mode; then
      echo "✗ Auto mode: AI review failed completely — not committing without review."
      echo "  Check connectivity/AI provider and re-run gpa --auto."
      return 1
    fi

    echo "Options:"
    echo "  [Enter] Retry"
    echo "  [i]     Ignore and proceed"
    echo "  [esc]   Cancel"
    echo ""
    echo -n "Your choice: "
    read -r skip_review

    case "$skip_review" in
      ""|$'\n')  # ENTER - Retry
        echo ""
        echo "♻️  Retrying review..."
        echo ""
        gpa "$@"
        return $?
        ;;
      i|I)  # Ignore
        echo "✓ Continuing without AI review"
        ;;
      $'\e'|q|Q|*)  # ESC or invalid - Cancel
        echo "✗ Aborting commit - changes remain staged"
        return 1
        ;;
    esac
  elif [ $failed_batches -gt 0 ]; then
    echo "⚠ Warning: $failed_batches of $batch_count batch(es) failed review (hard failures)"
  fi
  
  # Handle soft failures (unparseable responses)
  if [ $soft_failed_batches -gt 0 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠ WARNING: $soft_failed_batches batch(es) returned unparseable responses"
    echo ""
    echo "The AI reviewed your code but returned output that could not be parsed."
    echo "This means issues may have been found but weren't captured."
    echo ""

    if $auto_mode; then
      echo "✗ Auto mode: review response unparseable — not committing without a clean review."
      echo "  Re-run gpa --auto; if it persists, investigate the AI provider's output."
      return 1
    fi

    echo "Options:"
    echo "  [Enter] Retry"
    echo "  [i]     Ignore and proceed"
    echo "  [esc]   Cancel"
    echo ""
    echo -n "Your choice: "
    read -r soft_fail_choice

    case "$soft_fail_choice" in
      ""|$'\n')  # ENTER - Retry
        echo ""
        echo "♻️  Retrying review..."
        echo ""
        gpa "$@"
        return $?
        ;;
      i|I)  # Ignore
        echo "✓ Ignoring unparseable responses and continuing"
        ;;
      $'\e'|q|Q|*)  # ESC or invalid - Cancel
        echo "✗ Canceling review - changes remain staged"
        return 1
        ;;
    esac
  fi
  
  echo "═══════════════════════════════════════════════════════════"
  
  # Only findings that pass the guard (quoted added line, blocking category, not already reviewed, confirmed on a
  # second look) may block; everything else was reported above as dropped or advisory. See _gpa_guard_issues.
  if [ "$ai_review_failed" != true ]; then
    all_issues=$(_gpa_guard_issues "$all_issues")
    if [[ -s "${GPA_WAIVED_FILE:-}" ]]; then
      local waived_fp
      while read -r waived_fp; do
        AI_COMMIT_BODY="${AI_COMMIT_BODY:+$AI_COMMIT_BODY$'\n\n'}Review-waived: $waived_fp ${GPA_WAIVE_REASON:-}"
      done < "$GPA_WAIVED_FILE"
    fi
  fi

  # Count total issues found
  local total_issue_count=$(echo "$all_issues" | jq 'length')
  
  # Handle case where AI review was skipped or no issues found
  if [ "$ai_review_failed" = true ] || [ "$total_issue_count" -eq 0 ]; then
    # No issues found or review was skipped - proceed directly to commit
    if [ "$ai_review_failed" = true ]; then
      echo "ℹ Proceeding without AI review"
    else
      echo "✓ Code review complete - no blocking findings"
    fi

    if $auto_mode; then
      echo ""
      echo "ℹ Auto mode: committing and pushing"
      echo ""
      gpc
      local gpc_status=$?
      rm -f /tmp/gpa_secrets_verdict.txt
      return $gpc_status
    fi

    echo ""
    echo "Options:"
    echo "  [Enter] Commit and push (gpc)"
    echo "  [esc]   Cancel - keep staged"
    echo ""
    echo -n "Your choice: "
    _read_key
    echo ""

    case "$_KEY" in
      y | Y | $'\n')
        echo ""
        echo "✓ Proceeding to commit and push..."
        echo ""
        gpc
        return $?
        ;;
      *)
        echo "ℹ Keeping changes staged."
        return 0
        ;;
    esac
  else
    # Issues found - display summary
    echo "⚠ Found $total_issue_count issue(s) across all batches"
    echo ""

    # Display a summary of issues by severity
    local critical_count=$(echo "$all_issues" | jq '[.[] | select(type == "object" and .severity == "Critical")] | length' 2>/dev/null || echo "0")
    local warning_count=$(echo "$all_issues" | jq '[.[] | select(type == "object" and .severity == "Warning")] | length' 2>/dev/null || echo "0")

    if [ "$critical_count" -gt 0 ]; then
      echo "  🔴 Critical: $critical_count"
    fi
    if [ "$warning_count" -gt 0 ]; then
      echo "  🟡 Warning: $warning_count"
    fi
    echo ""

    if $auto_mode; then
      # Print full findings and hand control back to the caller instead of
      # entering the interactive fix loop or recursing into aidev — an
      # AI-agent caller is expected to read these, fix the files itself with
      # its own edit tools, then re-run `gpa --auto`. Changes stay staged.
      echo "Auto mode: not committing. Findings requiring a decision:"
      echo ""
      echo "$all_issues" | jq -r '.[] | "─────────────────────────────────────────────\nFile: \(.file)\nSeverity: \(.severity)\nIssue: \(.issue)\nRecommendation: \(.recommendation)\n"'
      echo "─────────────────────────────────────────────"
      print -r -- "$all_issues" | jq -r '.[] | select(.fingerprint) | "  \(.fingerprint)  \(.category)  \(.file): \(.evidence)"'
      echo "Fix these, then re-run 'gpa --auto' (changes remain staged). A finding you believe is wrong cannot be"
      echo "skipped from --auto: report it to the user, who can run gpa --waive <fingerprint> --reason '...' -m '...'."
      rm -f /tmp/gpa_secrets_verdict.txt
      return 3
    fi

    # Enter interactive fix mode
    echo "Entering interactive fix mode..."
    echo ""
    _gpa_interactive_fix "$all_issues"
    rm -f /tmp/gpa_secrets_verdict.txt
    return $?
  fi
  rm -f /tmp/gpa_secrets_verdict.txt
}
