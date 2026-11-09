# Helper function: decide which AI review findings may block the commit.
# Usage: _gpa_guard_issues '<json array of findings>'  -> the BLOCKING findings as a JSON array on stdout
# The rules are in ~/.config/aistack/gpa_review_guard.py (GPA_REVIEW_GUARD overrides the path): a finding must quote
# an added line of the staged diff, be Critical in a blocking category, and sit on a line that has not already passed
# an earlier round. What is left is shown to the model once more, alone with the code around its line, and blocks
# unless that second look rejects it (no verdict keeps it blocking). Dropped, advisory and waived findings are
# reported on stderr, never silently. GPA_WAIVE holds waived fingerprints (gpa --waive); the ones that matched a
# finding are written to GPA_WAIVED_FILE so the caller can record them in the commit message.
function _gpa_guard_issues() {
  local issues="$1"
  local guard="${GPA_REVIEW_GUARD:-${AISTACK_DIR:-$HOME/.config/aistack}/gpa_review_guard.py}"
  local waive_json out
  waive_json=$(print -r -- "${GPA_WAIVE:-}" | jq -Rc 'split(" ") | map(select(length > 0))')
  if [[ -f "$guard" ]] && command -v python3 >/dev/null; then
    out=$(jq -nc --argjson issues "$issues" --argjson waive "${waive_json:-[]}" '{issues: $issues, waive: $waive}' | python3 "$guard" guard)
  fi
  if [[ -z "$out" ]]; then
    echo "  ⚠ review guard unavailable ($guard): every finding blocks" >&2
    print -r -- "$issues"
    return 0
  fi
  jq -r '.dropped[] | "  (dropped, \(.why): \(.file): \((.issue // "") | tostring | .[0:100]))"' <<<"$out" >&2
  jq -r '.advisory[] | "  🟡 advisory, does not block (\(.why)): \(.file): \(.issue)"' <<<"$out" >&2
  jq -r '.waived[] | "  ⚪ waived \(.fingerprint): \(.file): \(.issue)"' <<<"$out" >&2
  [[ -n "${GPA_WAIVED_FILE:-}" ]] && jq -r '.waived[].fingerprint' <<<"$out" > "$GPA_WAIVED_FILE"

  local blocking="[]" n i item reply rc verdict
  n=$(jq '.blocking | length' <<<"$out")
  for (( i = 0; i < n; i++ )); do
    item=$(jq -c ".blocking[$i]" <<<"$out")
    echo "  Confirming finding $((i + 1)) of $n ($(jq -r '.file' <<<"$item"))..." >&2
    reply=$(print -r -- "A code reviewer reported the problem below about one line of a change. Decide whether it is real.

File: $(jq -r '.file' <<<"$item")
Reported problem ($(jq -r '.category' <<<"$item")): $(jq -r '.issue' <<<"$item")
The line it is about: $(jq -r '.evidence' <<<"$item")

The file around that line (the line is marked with >):
$(jq -r '.context' <<<"$item")

Answer CONFIRMED only if this line, as written and in this context, really has that problem and it would cause a
security hole, data loss or broken code. Answer REJECTED if the report is wrong, if the surrounding code or a comment
already handles it, or if it is a matter of style or preference.
Output ONLY a JSON array with one object and nothing else: [{\"verdict\": \"CONFIRMED\" or \"REJECTED\", \"reason\": \"one sentence\"}]" | _run_ai_direct 2>/dev/null)
    rc=$?
    verdict=$(jq -r '(if type == "array" then .[0] else . end) | .verdict // empty' <<<"$reply" 2>/dev/null)
    if [[ $rc -eq 0 && "${verdict:u}" == "REJECTED" ]]; then
      echo "  🟡 not confirmed on a second look, now advisory: $(jq -r '"\(.file): \(.issue)"' <<<"$item") -- $(jq -r '(if type == "array" then .[0] else . end) | .reason // ""' <<<"$reply" 2>/dev/null)" >&2
    else
      [[ "${verdict:u}" == "CONFIRMED" ]] || echo "  ⚠ the second look gave no verdict, so this finding keeps blocking" >&2
      blocking=$(jq -c --argjson it "$item" '. + [$it | del(.context)]' <<<"$blocking")
    fi
  done
  jq -nc --argjson b "$blocking" '{blocking: $b}' | python3 "$guard" settle >/dev/null
  print -r -- "$blocking"
}

# Helper function: Launch aidev inline with all issues as context
# Usage: _gpa_send_all_to_aidev <structured_issues_json>
# Returns 0 to re-review, 1 to keep staged
function _gpa_send_all_to_aidev() {
  local structured_issues="$1"
  local issue_count=$(echo "$structured_issues" | jq 'length' 2>/dev/null)
  local session_name="gpa-aidev-$$"

  # Build prompt file
  local prompt_file="/tmp/gpa_all_issues_$$.txt"
  printf "I have %s code review issue(s) in my staged git changes that need to be fixed. Please help me address each one.\n\n" "$issue_count" > "$prompt_file"

  local i=0
  while [ $i -lt "$issue_count" ]; do
    local issue=$(echo "$structured_issues" | jq -r ".[$i]" 2>/dev/null)
    local file=$(echo "$issue" | jq -r '.file // empty' 2>/dev/null)
    local severity=$(echo "$issue" | jq -r '.severity // empty' 2>/dev/null)
    local issue_desc=$(echo "$issue" | jq -r '.issue // empty' 2>/dev/null)
    local recommendation=$(echo "$issue" | jq -r '.recommendation // empty' 2>/dev/null)
    printf -- "---\nIssue %s of %s\nFile: %s\nSeverity: %s\nIssue: %s\nRecommendation: %s\n\n" \
      "$((i+1))" "$issue_count" "$file" "$severity" "$issue_desc" "$recommendation" >> "$prompt_file"
    ((i++))
  done
  printf "Please fix all of these issues. After fixing, I'll re-stage the affected files." >> "$prompt_file"

  # Capture staged files and their hashes before running aidev
  local repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  local staged_files=()
  while IFS= read -r f; do
    staged_files+=("$f")
  done < <(git diff --cached --name-only)

  # Snapshot content hashes of each staged file before aidev runs
  local -A pre_hashes
  for f in "${staged_files[@]}"; do
    local abs="$repo_root/$f"
    if [[ -f "$abs" ]]; then
      pre_hashes[$f]=$(shasum -a 256 "$abs" | cut -d' ' -f1)
    fi
  done

  echo ""
  echo "=== aidev: Fix All Issues ==="
  echo ""
  # Blocking (gpa re-reviews afterwards): one aidev -p edit by a free builder, limited to the staged files.
  (cd "$repo_root" && aidev -p "The staged changes in this repository failed code review. Evaluate each finding below (some may be false positives) and fix the real ones in the working tree. Change nothing else.

$(cat "$prompt_file")" "${staged_files[@]}")
  rm -f "$prompt_file"

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "aidev session complete."
  echo "═══════════════════════════════════════════════════════════"
  echo ""
  echo "  [Enter] Re-review with gpa"
  echo "  [esc]   Keep staged as-is"
  echo ""
  echo -n "Your choice: "
  _read_key
  echo ""

  case "$_KEY" in
    $'\n' | $'\r')
      echo ""
      # Re-stage all files, but only re-review files aidev actually changed
      local changed_files=()
      for f in "${staged_files[@]}"; do
        local abs="$repo_root/$f"
        git -C "$repo_root" add "$f" 2>/dev/null
        local post_hash=""
        if [[ -f "$abs" ]]; then
          post_hash=$(shasum -a 256 "$abs" | cut -d' ' -f1)
        fi
        if [[ "${pre_hashes[$f]}" != "$post_hash" ]]; then
          changed_files+=("$f")
        fi
      done

      if [[ ${#changed_files[@]} -eq 0 ]]; then
        echo "ℹ aidev made no file changes — skipping re-review"
        echo ""
        echo "Options:"
        echo "  [Enter] Commit and push (gpc)"
        echo "  [r]     Force re-review"
        echo "  [esc]   Keep staged"
        echo ""
        echo -n "Your choice: "
        _read_key
        echo ""
        case "$_KEY" in
          y | Y | $'\n') gpc; return $? ;;
          r | R) gpa; return $? ;;
          *) echo "ℹ Keeping changes staged."; return 0 ;;
        esac
      fi

      echo "ℹ aidev modified ${#changed_files[@]} file(s) — re-reviewing only those"
      echo ""
      # Pass the changed files as a filter to a targeted gpa re-review
      _gpa_review_files "${changed_files[@]}"
      return $?
      ;;
    *)
      echo "ℹ Keeping changes staged."
      return 0
      ;;
  esac
}

