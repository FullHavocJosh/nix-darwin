# Helper function: Run the AI review + interactive fix loop on a specific subset of files
# Usage: _gpa_review_files file1 file2 ...
function _gpa_review_files() {
  local target_files=("$@")

  # Build a batch from only the specified files (as a JSON array)
  local batch="[]"
  for f in "${target_files[@]}"; do
    batch=$(echo "$batch" | jq --arg f "$f" '. += [$f]')
  done

  local batch_count=1

  echo "═══════════════════════════════════════════════════════════"
  echo "ℹ Re-reviewing ${#target_files[@]} changed file(s)..."
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "⚪ $(_llamacpp_model_short) — Reviewing ${#target_files[@]} file(s)... [llama.cpp]"
  local batch_issues
  batch_issues=$(_gpa_review_batch_with_timeout "$batch" "1" "1" "auto")
  local review_status=$?

  if [[ $review_status -ne 0 ]] || ! echo "$batch_issues" | jq empty 2>/dev/null; then
    echo "  ⚠ Review failed or returned invalid JSON"
    echo ""
    echo "Options:"
    echo "  [Enter] Commit and push (gpc)"
    echo "  [esc]   Keep staged"
    echo ""
    echo -n "Your choice: "
    _read_key; echo ""
    case "$_KEY" in
      y | Y | $'\n') gpc; return $? ;;
      *) echo "ℹ Keeping changes staged."; return 0 ;;
    esac
  fi

  local valid_issues=$(echo "$batch_issues" | jq '[.[] | select(type == "object" and has("file") and has("severity") and has("issue") and has("recommendation"))]' 2>/dev/null)
  local issue_count=$(echo "$valid_issues" | jq 'length')

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  if [[ "$issue_count" -eq 0 ]]; then
    echo "✓ Re-review complete — no issues found in changed files"
  else
    echo "⚠ Re-review found $issue_count remaining issue(s) — showing for reference"
    echo ""
    local ci=0
    while [[ $ci -lt $issue_count ]]; do
      local iss=$(echo "$valid_issues" | jq -r ".[$ci]" 2>/dev/null)
      local isev=$(echo "$iss" | jq -r '.severity // empty')
      local ifile=$(echo "$iss" | jq -r '.file // empty')
      local idesc=$(echo "$iss" | jq -r '.issue // empty')
      echo "  [$isev] $ifile — $idesc"
      ((ci++))
    done
  fi
  echo ""
  echo "Options:"
  echo "  [Enter] Commit and push (gpc)"
  echo "  [esc]   Keep staged — fix manually and re-run gpa"
  echo ""
  echo -n "Your choice: "
  _read_key; echo ""
  case "$_KEY" in
    y | Y | $'\n') gpc; return $? ;;
    *) echo "ℹ Keeping changes staged."; return 0 ;;
  esac
}

