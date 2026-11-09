# Helper function: Review a batch of files and return structured issues
# Usage: _gpa_review_batch <batch_files_json> <batch_number> <total_batches> [tier_override]
function _gpa_review_batch() {
  local batch_files_json="$1"
  local batch_number="$2"
  local total_batches="$3"
  local tier_override="${4:-auto}"  # Optional: "haiku", "sonnet", "opus", or "auto"
  
  # Convert JSON array to regular array
  local batch_files=()
  while IFS= read -r file; do
    batch_files+=("$file")
  done < <(echo "$batch_files_json" | jq -r '.[]')
  
  if [ ${#batch_files[@]} -eq 0 ]; then
    echo "[]"
    return 0
  fi
  
  # Get diff for only these files
  local batch_diff=""
  for file in "${batch_files[@]}"; do
    batch_diff="${batch_diff}$(git diff --cached -- "$file")\n"
  done

  # Build surrounding context: 40 lines before/after each changed hunk from the full file
  # This lets the reviewer see nearby comments/guards without scanning the whole file
  local batch_context=""
  for file in "${batch_files[@]}"; do
    if [[ -f "$file" ]]; then
      # Extract changed line numbers from the diff hunk headers, then grab context lines
      local changed_lines
      changed_lines=$(git diff --cached -- "$file" | grep "^@@" | \
        sed 's/.*+\([0-9]*\).*/\1/' | head -20)
      if [[ -n "$changed_lines" ]]; then
        batch_context="${batch_context}
=== Surrounding context: $file ===
"
        while IFS= read -r start_line; do
          local ctx_start=$(( start_line > 40 ? start_line - 40 : 1 ))
          local ctx_end=$(( start_line + 40 ))
          batch_context="${batch_context}$(awk "NR>=${ctx_start} && NR<=${ctx_end} {print NR\": \"\$0}" "$file")
---
"
        done <<< "$changed_lines"
      fi
    fi
  done
  
  # Count lines in this batch
  local batch_lines=$(echo -e "$batch_diff" | wc -l)
  
  # "auto" reviews on the local model; gpa --tier=<haiku|sonnet|opus> and "cloud-escalation" go to Claude Code
  local ai_tier="local"
  [[ "$tier_override" != "auto" ]] && ai_tier="$tier_override"
  # Check if any Terraform files are in this batch
  local has_terraform=false
  for file in "${batch_files[@]}"; do
    if [[ "$file" == *.tf ]]; then
      has_terraform=true
      break
    fi
  done
  
  # Build review prompt
  local review_prompt="Review the following staged git changes for CRITICAL ISSUES AND WARNINGS ONLY:

🔴 **CRITICAL - Must Fix Before Commit:**
1. **SECRETS & CREDENTIALS**: API keys, passwords, tokens, private keys, connection strings, AWS credentials, OAuth secrets, certificates. NOTE: Environment variable references like \${VAR_NAME} or \$VAR_NAME are NOT hardcoded credentials — do not flag them.
2. **Bugs**: Syntax errors, runtime errors, null pointer dereferences, infinite loops
3. **Security Vulnerabilities**: SQL injection, command injection, XSS, insecure crypto, path traversal
4. **Data Loss**: Destructive operations without safeguards, missing transactions, race conditions

🟡 **WARNINGS - Should Consider:**
5. **Security Concerns**: Overly permissive permissions, missing input validation, unsafe eval, hardcoded IPs/domains
6. **Logic Flaws**: Off-by-one errors, incorrect conditionals, missing edge cases
7. **Breaking Changes**: API changes, removed functionality, incompatible updates"
  
  if [ "$has_terraform" = true ]; then
    review_prompt="$review_prompt

**TERRAFORM-SPECIFIC CRITICAL/WARNING CHECKS** (detected .tf files):
🔴 **Critical**: Hardcoded secrets/keys, publicly exposed resources, destructive changes without lifecycle protection
🟡 **Warnings**: Overly permissive IAM (wildcards in production), missing encryption, expensive resources without justification"
  fi
  
  # Include secrets analysis verdict if available
  local secrets_context=""
  if [[ -f /tmp/gpa_secrets_verdict.txt ]]; then
    if [[ -s /tmp/gpa_secrets_verdict.txt ]]; then
      secrets_context="

PRIOR SECURITY ANALYSIS — Secrets detection already analyzed the following items and determined they are FALSE POSITIVES. Do NOT re-flag these:
$(cat /tmp/gpa_secrets_verdict.txt | head -30)

Secrets in your diff that match these patterns have ALREADY been verified as safe (placeholder examples, runtime-generated values, or template variable references). If a detection matches one of these, do NOT include it in your output."
    fi
  fi

  # Build full prompt
  local full_prompt="${review_prompt}${secrets_context}

Batch ${batch_number} of ${total_batches} (${batch_lines} lines)

Files in this batch:
$(printf '%s\n' "${batch_files[@]}")

Git diff:
${batch_diff}
${batch_context}
**IMPORTANT INSTRUCTIONS:**
- ONLY report 🔴 Critical issues and 🟡 Warnings
- IGNORE minor suggestions, style preferences, and code quality opinions
- Focus on things that will actually break, cause security issues, or have serious consequences
- ONLY flag issues that are INTRODUCED OR WORSENED by lines marked with + in the diff — do NOT flag pre-existing code in unchanged lines
- The surrounding context is provided so you can see if a nearby comment, guard clause, or existing code ALREADY mitigates the concern — if so, do NOT flag it
- If the code or a comment already acknowledges a known limitation, do NOT flag it as an issue
- If a prior security analysis has already confirmed an item is a false positive, do NOT flag it
- Every issue MUST include \"evidence\": ONE line copied exactly from the diff, a line that starts with + (leave the + out). An issue whose evidence is not an added line of that file is discarded, so never describe code you cannot quote.
- Every issue MUST include \"category\", one of: secret-exposure, injection, destructive-command, broken-syntax, auth-bypass, other. Use \"other\" for anything else; only the first five can block a commit.
- Report at most 10 issues, most severe first, and keep each \"recommendation\" under 40 words
- Inside the JSON string values use single quotes only, never double quotes or raw newlines, so the JSON stays valid
- Output ONLY a JSON array of issues in this exact format:
[
  {
    \"file\": \"path/to/file.ext\",
    \"severity\": \"Critical\" or \"Warning\",
    \"issue\": \"Brief issue description\",
    \"recommendation\": \"Detailed fix recommendation\",
    \"category\": \"injection\",
    \"evidence\": \"the exact added line this is about\"
  }
]
- If there are no critical/warning issues in this batch, return an empty array: []
- Return ONLY valid JSON, nothing else."
  
  # Note: Tier display moved to main loop for better visibility
  # (was being cleared by progress spinner)

  # ── Route the API call ──────────────────────────────────────────────────────
  # "local"            → llama.cpp via _run_ai_direct; a hard failure falls back to Claude Code sonnet unless
  #                      AI_LOCAL_ONLY (gpa-local, or AI_LOCAL_DEFAULT hosts)
  # "cloud-escalation" → Claude Code sonnet via _run_ai_direct_claude
  # haiku/sonnet/opus  → Claude Code with that model (gpa --tier=...)
  local batch_result
  local api_exit_code

  if [[ "$ai_tier" == "local" ]]; then
    echo "  ⚪ Using local model [llama.cpp / $(_llamacpp_model_short)]" >&2
    batch_result=$(echo "$full_prompt" | _run_ai_direct 2>&1)
    api_exit_code=$?
    if [ $api_exit_code -eq 1 ] && [[ -z "$AI_LOCAL_ONLY" ]]; then
      echo "  ⚠ Local model failed — falling back to Claude Code sonnet..." >&2
      batch_result=$(echo "$full_prompt" | _run_ai_direct_claude sonnet 2>&1)
      api_exit_code=$?
    fi
  else
    local _claude_model="$ai_tier"
    [[ "$ai_tier" == "cloud-escalation" ]] && _claude_model="sonnet"
    echo "  ☁  Using Claude Code [$_claude_model]" >&2
    batch_result=$(echo "$full_prompt" | _run_ai_direct_claude "$_claude_model" 2>&1)
    api_exit_code=$?
  fi
  # Check exit codes
  if [ $api_exit_code -eq 1 ]; then
    # Hard failure - API error, timeout, network issue
    echo "  ✗ API Error" >&2
    echo "[]"
    return 1
  elif [ $api_exit_code -eq 2 ]; then
    # Soft failure - unparseable response
    echo "  ⚠ AI response could not be parsed" >&2
    echo "[]"
    return 2
  fi
  
  # Empty output is not "no issues found" (jq empty accepts empty input)
  if [[ -z "${batch_result//[[:space:]]/}" ]]; then
    echo "  ⚠ AI returned empty response" >&2
    echo "[]"
    return 2
  fi

  # Success (exit code 0) - validate and return
  if echo "$batch_result" | jq empty 2>/dev/null; then
    echo "$batch_result"
    return 0
  fi
  
  # Shouldn't reach here if _run_ai_direct works correctly, but handle it
  echo "  ⚠ Unexpected: Valid exit code but invalid JSON" >&2
  echo "[]"
  return 2
}

