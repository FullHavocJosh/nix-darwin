# Helper function: Check if a file contains Helm template syntax
# Usage: _is_helm_template <file_path>
# Returns 0 if file is a Helm template, 1 otherwise
function _is_helm_template() {
  local file="$1"
  
  # Check if file is in a Helm chart templates directory (path-based detection)
  # This works even if the file path is relative
  if [[ "$file" == *"/charts/"*"/templates/"* ]] || [[ "$file" == *"/helm/"*"/templates/"* ]]; then
    return 0
  fi
  
  # Check file content for Helm template syntax (only if file exists)
  if [ -f "$file" ]; then
    # Look for common Helm template patterns
    if grep -qE '\{\{-?\s*(include|define|template|if|range|with|\.Values\.|\.Release\.|\.Chart\.|toYaml|nindent)' "$file" 2>/dev/null; then
      return 0
    fi
  fi
  
  return 1
}

# Helper function: Run linters on staged files
# Returns 0 if all linters pass or user wants to continue, 1 if user wants to abort
function _run_linters() {
  local auto_mode="${1:-false}"
  local recheck="${2:-false}"   # true on the pass after auto-fix: issues that remain are final, never fix again (no recursion)
  local files=()
  while IFS= read -r file; do
    # a symlink is linted at its target; prettier refuses symlinks ("is a symbolic link") and the check never passes
    [[ -L "$file" ]] && continue
    files+=("$file")
  done < <(git diff --cached --name-only)
  
  if [ ${#files[@]} -eq 0 ]; then
    return 0
  fi
  
  local linting_issues=false
  local lint_report=""
  local oxfmt_rc
  local files_with_issues=()
  
  # Check for available linters and verify they work
  local has_nixfmt=false
  local nixfmt_broken=false
  if command -v nixfmt &>/dev/null; then
    local nixfmt_path=$(command -v nixfmt)
    # Check if it's a real binary (not just a text file placeholder)
    if file "$nixfmt_path" | grep -qE "(executable|ELF|Mach-O)"; then
      # Verify nixfmt actually works (not just a placeholder file)
      if nixfmt --version &>/dev/null || nixfmt --help &>/dev/null; then
        has_nixfmt=true
      else
        nixfmt_broken=true
      fi
    else
      # It's a text file or script placeholder
      nixfmt_broken=true
    fi
  fi
  
  local has_prettier=false
  if command -v prettier &>/dev/null; then
    if prettier --version &>/dev/null; then
      has_prettier=true
    fi
  fi
  
  local has_ruff=false
  if command -v ruff &>/dev/null; then
    if ruff --version &>/dev/null; then
      has_ruff=true
    fi
  fi
  
  local has_shellcheck=false
  command -v shellcheck &>/dev/null && has_shellcheck=true

  # Track files that need linters but linters are unavailable
  local missing_linters=false
  local missing_linters_report=""
  
  # Declare once, outside the loop: a bare `local x` on an already-set var makes zsh print it (the ruff_output=$'...' dumps).
  # Assign separately: `local x=$(cmd)` makes $? the exit status of `local` (always 0), which hid every linter failure.
  local ruff_output ruff_exit sc_output sc_exit zn_output

  # Run linters based on file types
  for file in "${files[@]}"; do
    # Skip deleted files
    if [ ! -f "$file" ]; then
      continue
    fi
    
    local file_has_issues=false
    
    case "$file" in
      *.nix)
        if $has_nixfmt; then
          if ! nixfmt --check "$file" 2>/dev/null; then
            lint_report="${lint_report}🟡 $file: nixfmt formatting issues\n"
            linting_issues=true
            file_has_issues=true
          fi
        elif $nixfmt_broken; then
          missing_linters_report="${missing_linters_report}⚠️  $file: nixfmt is broken/unavailable\n"
          missing_linters=true
        else
          missing_linters_report="${missing_linters_report}⚠️  $file: nixfmt not installed\n"
          missing_linters=true
        fi
        ;;
      *.js|*.jsx|*.ts|*.tsx|*.json|*.md|*.yml|*.yaml|*.css|*.html)
        # Skip Prettier for Helm chart templates
        if [[ "$file" == *.yml ]] || [[ "$file" == *.yaml ]]; then
          if _is_helm_template "$file"; then
            continue  # Skip linting for Helm templates
          fi
        fi
        
        case "$(_repo_formatter "$file")" in
          oxfmt)
            _oxfmt_file check "$file"
            oxfmt_rc=$?
            if [[ $oxfmt_rc -eq 127 ]]; then
              missing_linters_report="${missing_linters_report}⚠️  $file: oxfmt not installed (install the repo's dependencies)\n"
              missing_linters=true
            elif [[ $oxfmt_rc -ne 0 ]]; then
              lint_report="${lint_report}🟡 $file: oxfmt formatting issues\n"
              linting_issues=true
              file_has_issues=true
            fi
            ;;
          biome|dprint)
            : # this repo formats with its own tool; prettier would rewrite the file against the wrong style
            ;;
          *)
            if $has_prettier; then
              if ! prettier --check "$file" 2>/dev/null; then
                lint_report="${lint_report}🟡 $file: prettier formatting issues\n"
                linting_issues=true
                file_has_issues=true
              fi
            else
              missing_linters_report="${missing_linters_report}⚠️  $file: prettier not installed\n"
              missing_linters=true
            fi
            ;;
        esac
        ;;
      *.py)
        if $has_ruff; then
          ruff_output=$(ruff check "$file" 2>&1)
          ruff_exit=$?
          # ruff returns non-zero exit code when issues are found
          # Don't check output text as "All checks passed!" is also output
          if [ $ruff_exit -ne 0 ]; then
            lint_report="${lint_report}🟡 $file: ruff linting issues\n"
            lint_report="${lint_report}   $(echo "$ruff_output" | head -3 | sed 's/^/   /')\n"
            linting_issues=true
            file_has_issues=true
          fi
        else
          missing_linters_report="${missing_linters_report}⚠️  $file: ruff not installed\n"
          missing_linters=true
        fi
        ;;
      *.sh|*.bash)
        # shellcheck only understands sh/bash/dash/ksh; zsh scripts (most of this repo's) are left to `zsh -n`.
        # Errors only: warnings and style notes on existing scripts would block commits without a real defect.
        if head -1 "$file" | grep -qE '^#!.*(/|env +)(ba|da|k)?sh( |$)'; then
          if $has_shellcheck; then
            sc_output=$(shellcheck --severity=error "$file" 2>&1)
            sc_exit=$?
            if [ $sc_exit -ne 0 ]; then
              lint_report="${lint_report}🟡 $file: shellcheck errors\n"
              lint_report="${lint_report}   $(echo "$sc_output" | head -6 | sed 's/^/   /')\n"
              linting_issues=true
              file_has_issues=true
            fi
          else
            missing_linters_report="${missing_linters_report}⚠️  $file: shellcheck not installed\n"
            missing_linters=true
          fi
        elif head -1 "$file" | grep -qE '^#!.*zsh'; then
          if ! zn_output=$(zsh -n "$file" 2>&1); then
            lint_report="${lint_report}🟡 $file: zsh syntax error\n   $(echo "$zn_output" | head -3)\n"
            linting_issues=true
            file_has_issues=true
          fi
        fi
        ;;
    esac
    
    if $file_has_issues; then
      files_with_issues+=("$file")
    fi
  done
  
  # Display missing linters warnings if any
  if $missing_linters; then
    echo ""
    echo "⚠️  MISSING OR BROKEN LINTERS"
    echo ""
    echo -e "$missing_linters_report"
    echo "ℹ  Some files could not be checked. Install missing linters:"
    if ! $has_nixfmt || $nixfmt_broken; then
      echo "    • nixfmt: Install via your system package manager or nix profile"
      if $nixfmt_broken; then
        echo "      (Note: Current nixfmt at $(command -v nixfmt) is broken)"
      fi
    fi
    if ! $has_prettier; then
      echo "    • prettier: npm install -g prettier"
    fi
    if ! $has_ruff; then
      echo "    • ruff: pip install ruff or install via system package manager"
    fi
    echo ""
  fi
  
  if $linting_issues; then
    echo ""
    echo "⚠️  LINTING ISSUES DETECTED"
    echo ""
    echo -e "$lint_report"
    echo ""
    local lint_choice
    if $auto_mode && $recheck; then
      echo "✗ Linting issues remain after auto-fix. Fix them (or the linter's rules) and run again."
      return 1
    elif $auto_mode; then
      echo "ℹ Auto mode: auto-fixing formatting issues"
      lint_choice="f"
    else
      # On recheck, [f] already ran: offering it again only loops on rules the linter can't fix
      if $recheck; then
        echo "ℹ Remaining issues are not auto-fixable; edit the files or ignore."
        echo ""
      fi
      echo "Options:"
      echo "  [e] Edit files with AI assistance (opens an nvim + aidev workspace)"
      $recheck || echo "  [f] Auto-fix formatting issues (where possible)"
      echo "  [i] Ignore and continue"
      echo "  [q] Quit and fix manually"
      echo ""
      echo -n "Your choice: "
      read -r lint_choice
    fi
    
    case "$lint_choice" in
      e | E)
        echo ""
        echo "ℹ Opening a workspace for manual fixes with AI assistance..."
        echo "  nvim tab: files with issues"
        echo "  aidev tab: aidev assistant"
        echo ""

        # Convert files_with_issues array to newline-separated string
        local files_string=$(printf '%s\n' "${files_with_issues[@]}")

        _linter_create_edit_workspace "$files_string" "$lint_report"

        # Wait for user to finish editing
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "⏸  Waiting for you to finish editing..."
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        echo "When you're done editing in the new workspace:"
        echo "  1. Save your changes in nvim"
        echo "  2. Switch back to this pane"
        echo "  3. Press Enter here to re-run linting checks"
        echo ""
        echo -n "Press Enter when editing is complete: "
        read -r
        
        # Re-stage the files
        echo ""
        echo "ℹ Re-staging modified files..."
        for file in "${files_with_issues[@]}"; do
          if [ -f "$file" ]; then
            git add "$file"
            echo "  ✓ Re-staged: $file"
          fi
        done
        
        # Re-run linting checks
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "ℹ Re-running linting checks..."
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        
        # Recursively call _run_linters to check again
        _run_linters "$auto_mode" true
        return $?
        ;;
      f | F)
        if $recheck; then
          echo "✗ Auto-fix already ran; remaining issues need a manual fix."
          return 1
        fi
        echo ""
        echo "ℹ Auto-fixing formatting issues..."
        for file in "${files_with_issues[@]}"; do
          if [ ! -f "$file" ]; then
            continue
          fi
          
          case "$file" in
            *.nix)
              if $has_nixfmt; then
                echo "  Formatting $file with nixfmt..."
                if nixfmt "$file" 2>&1; then
                  echo "  ✓ Formatted: $file"
                  git add "$file"
                else
                  echo "  ✗ Failed to format: $file"
                fi
              fi
              ;;
            *.js|*.jsx|*.ts|*.tsx|*.json|*.md|*.yml|*.yaml|*.css|*.html)
              # Skip Prettier for Helm chart templates
              if [[ "$file" == *.yml ]] || [[ "$file" == *.yaml ]]; then
                if _is_helm_template "$file"; then
                  echo "  ⊳ Skipping Helm template: $file"
                  continue
                fi
              fi
              
              case "$(_repo_formatter "$file")" in
                oxfmt)
                  echo "  Formatting $file with oxfmt..."
                  _oxfmt_file write "$file"
                  oxfmt_rc=$?
                  if [[ $oxfmt_rc -eq 0 ]]; then
                    echo "  ✓ Formatted: $file"
                    git add "$file"
                  elif [[ $oxfmt_rc -eq 127 ]]; then
                    echo "  ⊳ Skipping $file: oxfmt is not installed (install the repo's dependencies)"
                  else
                    echo "  ✗ Failed to format: $file"
                  fi
                  ;;
                biome|dprint)
                  echo "  ⊳ Skipping prettier for $file: the repo formats with its own tool"
                  ;;
                *)
                  if $has_prettier; then
                    echo "  Formatting $file with prettier..."
                    if prettier --write "$file" 2>&1; then
                      echo "  ✓ Formatted: $file"
                      git add "$file"
                    else
                      echo "  ✗ Failed to format: $file"
                    fi
                  fi
                  ;;
              esac
              ;;
            *.py)
              # EXE001: ruff never changes file modes, so make shebang files executable here
              if [[ ! -x "$file" ]] && head -1 "$file" | grep -q '^#!'; then
                chmod +x "$file"
                echo "  ✓ chmod +x (shebang): $file"
              fi
              if $has_ruff; then
                echo "  Checking $file with ruff..."
                if ruff check --fix "$file" 2>&1; then
                  echo "  ✓ Fixed: $file"
                else
                  echo "  ✗ Not auto-fixable: $file"
                fi
              fi
              # stage even on failure: a partial ruff fix or chmod must not be left unstaged
              git add "$file"
              ;;
          esac
        done
        echo ""
        echo "✓ Auto-fix complete. Files re-staged."
        
        # Re-run linting checks to verify fixes
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "ℹ Re-running linting checks to verify fixes..."
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        _run_linters "$auto_mode" true
        return $?
        ;;
      i | I)
        echo "⚠️  Proceeding with linting issues!"
        return 0
        ;;
      *)
        echo "✗ Aborting. Fix linting issues manually."
        return 1
        ;;
    esac
  elif ! $missing_linters; then
    # Only show "all good" if we actually checked everything
    echo "✓ No linting issues detected"
  fi
  
  return 0
}

