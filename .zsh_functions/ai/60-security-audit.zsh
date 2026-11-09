# Security audit function for AI configuration files
function ai_security_audit() {
  local RED='\033[0;31m'
  local GREEN='\033[0;32m'
  local YELLOW='\033[1;33m'
  local NC='\033[0m'
  
  echo "═══════════════════════════════════════════════════════════"
  echo "AI Configuration Security Audit"
  echo "═══════════════════════════════════════════════════════════"
  echo ""
  
  local issues_found=0
  
  # Check ~/.zshrc_envvars permissions
  if [[ -f ~/.zshrc_envvars ]]; then
    # macOS stat command
    local perms=""
    perms=$(stat -f "%Op" ~/.zshrc_envvars 2>/dev/null | tail -c 4)
    
    echo "Checking ~/.zshrc_envvars..."
    if [[ "$perms" == "0600" ]] || [[ "$perms" == "600" ]]; then
      echo "  ${GREEN}✓${NC} File permissions: 600 (secure)"
    else
      echo "  ${RED}✗${NC} File permissions: $perms (INSECURE)"
      echo "    Recommended: Run 'chmod 600 ~/.zshrc_envvars'"
      issues_found=$((issues_found + 1))
    fi
    
    # Check if file contains API keys
    if grep -q "API_KEY" ~/.zshrc_envvars; then
      echo "  ${YELLOW}ℹ${NC}  Contains API keys (stored in plain text)"
    fi
  else
    echo "~/.zshrc_envvars: Not found"
  fi
  
  echo ""
  
  if [[ -f ~/.zshrc_envvars_insecure ]] || [[ -L ~/.zshrc_envvars_insecure ]]; then
    local target_file=$(readlink -f ~/.zshrc_envvars_insecure 2>/dev/null || realpath ~/.zshrc_envvars_insecure 2>/dev/null || echo ~/.zshrc_envvars_insecure)

    local perms=""
    perms=$(stat -f "%Op" "$target_file" 2>/dev/null | tail -c 4)

    echo "Checking ~/.zshrc_envvars_insecure..."
    if [[ -L ~/.zshrc_envvars_insecure ]]; then
      echo "  ${YELLOW}ℹ${NC}  Symlink to: $target_file"
    fi
    if [[ "$perms" == "0600" ]] || [[ "$perms" == "600" ]]; then
      echo "  ${GREEN}✓${NC} File permissions: 600 (secure)"
    else
      echo "  ${RED}✗${NC} File permissions: $perms (INSECURE)"
      if [[ -L ~/.zshrc_envvars_insecure ]]; then
        echo "    Recommended: Run 'chmod 600 $target_file'"
      else
        echo "    Recommended: Run 'chmod 600 ~/.zshrc_envvars_insecure'"
      fi
      issues_found=$((issues_found + 1))
    fi
    
    if grep -q "API_KEY" "$target_file" 2>/dev/null; then
      echo "  ${RED}✗${NC} Contains API keys (should be in ~/.zshrc_envvars instead)"
      issues_found=$((issues_found + 1))
    fi
  fi
  
  echo ""
  
  if [[ -n "$OPENCODE_ZEN_API_KEY" ]]; then
    echo "Environment variables:"
    echo "  ${GREEN}✓${NC} OPENCODE_ZEN_API_KEY is set"
  fi
  
  if [[ -n "$OPENROUTER_API_KEY" ]]; then
    echo "  ${GREEN}✓${NC} OPENROUTER_API_KEY is set"
  fi
  
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  
  if [[ $issues_found -eq 0 ]]; then
    echo "${GREEN}✓${NC} No security issues found"
  else
    echo "${RED}✗${NC} Found $issues_found security issue(s)"
  fi
  
  echo "═══════════════════════════════════════════════════════════"
}

