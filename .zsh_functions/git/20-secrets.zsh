# Helper: return filenames (indented) from staged diff matching a grep pattern
function _get_matching_files() {
  local pattern="$1"
  git diff --cached --name-only | while IFS= read -r file; do
    if git diff --cached -- "$file" | grep "^+" | grep -v "^+++" | grep -qiE -- "$pattern"; then
      echo "    $file"
    fi
  done
}
# Scans stdin (added diff lines) for identifier = "value" / identifier: "value"
# assignments where the value is 20+ chars and high-entropy, regardless of
# what the identifier is named -- the keyword checks in _check_for_secrets
# only fire for specific names (password, api_key, token, secret). This
# catches a real secret assigned to anything else (DB_CONN, WEBHOOK_SIG,
# a typo'd name, an unfamiliar internal convention).
#
# Threshold is picked per apparent charset since max possible entropy differs:
# hex has only 16 symbols (max 4.0 bits/char) so real hex secrets still read
# as high entropy well below that ceiling; base64/mixed charsets go up to 6
# bits/char, so English-like or structured text sits much lower relative to
# a real random value even at the same length.
#
# Output: one flagged match per line, tab-separated (redacted-value, entropy,
# full source line) -- redaction keeps only the first/last 4 chars so the
# report itself never contains the actual secret value.
function _entropy_scan_secrets() {
  python3 -c "
import sys, re, math
from collections import Counter

DENY_VALUES = {
    'changeme', 'change_me', 'password', 'passwd', 'secret', 'example',
    'placeholder', 'foobar', 'test', 'dummy', 'fake', 'sample',
}

# Public content-addressable checksums are supposed to be high-entropy --
# that's the whole point of a hash. Nix (sha256/outputHash/narHash/vendorHash/
# cargoHash package pinning), npm/yarn (integrity), and general (md5/sha1/
# sha512/digest/checksum) all use these field names for values that are
# never secret. Matched as a substring against the key so e.g. "vendorHash"
# and "cargoSha256" both hit without listing every real-world variant.
DENY_KEY_SUBSTRINGS = (
    'sha256', 'sha512', 'sha1', 'md5', 'hash', 'integrity', 'checksum',
    'digest',
)

# Terraform Cloud/Enterprise resource IDs (workspace, variable set,
# workspace variable, run, policy, policy set, team, state version, run
# trigger, notification config, agent pool, org token) are HashiCorp's own
# opaque identifiers -- intentionally high-entropy by design, but public
# resource references routinely committed in version control (ops-meta.yaml,
# .tf/.tfvars), never secrets themselves. varset-5wmb2JhJyap54iuo and
# ws-nzYBA3TcUc1ayfSR are the two shapes that prompted this.
TFC_RESOURCE_ID_RE = re.compile(
    r'^(ws|var|varset|run|apply|plan|cv|pol|polset|team|sv|rt|notif|agent|agentpool|oc|at)-[A-Za-z0-9]{10,}$'
)

# Code identifiers (CamelCase / snake_case names such as the OOXML schema types CT_TextCharacterProperties and
# ST_HyperlinkSymbol in the Office skills, enum names, class names) read as high-entropy because they are long and
# mixed-case, but they are words. A random secret of letters only is unlikely (a 20-char base62 token has no digit
# 3 percent of the time) and has few vowels (about 19 percent of letters), identifiers about 30 to 40 percent.
SCHEMA_TYPE_RE = re.compile(r'^(CT|ST|EG|AG)_[A-Za-z0-9_]+$')

def looks_like_identifier(value):
    if SCHEMA_TYPE_RE.match(value):
        return True
    if not re.fullmatch(r'[A-Za-z]+(_[A-Za-z]+)*', value) or len(value) > 64:
        return False                     # digits, +/= or other symbols: could be a real secret
    boundaries = value.count('_') + len(re.findall(r'[a-z][A-Z]', value))
    letters = [c for c in value if c.isalpha()]
    vowel_ratio = sum(c in 'aeiouAEIOU' for c in letters) / len(letters)
    return boundaries >= 1 and vowel_ratio >= 0.28

def shannon_entropy(s):
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())

def entropy_threshold(value):
    if re.fullmatch(r'[0-9a-fA-F]+', value):
        return 3.0
    if re.fullmatch(r'[A-Za-z0-9+/=]+', value):
        return 4.5
    return 4.0

ASSIGN_RE = re.compile(r'''(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*['\"](?P<value>[A-Za-z0-9+/=_-]{20,})['\"]''')

for line in sys.stdin:
    line = line.rstrip('\n')
    for m in ASSIGN_RE.finditer(line):
        key = m.group('key')
        value = m.group('value')
        klower = key.lower()
        vlower = value.lower()
        if any(sub in klower for sub in DENY_KEY_SUBSTRINGS):
            continue  # known checksum/hash field, high entropy by design, not a secret
        if vlower in DENY_VALUES:
            continue
        if re.fullmatch(r'\\\$\{?[A-Za-z_][A-Za-z0-9_]*\}?', value):
            continue  # \$VAR / \${VAR} reference, not a literal value
        if re.fullmatch(r'\{\{.*\}\}', value):
            continue  # {{ template }} placeholder
        if re.fullmatch(r'[A-Z][A-Z0-9_]{7,}', value):
            continue  # ALL_CAPS_PLACEHOLDER style, same exclusion the password check uses
        if TFC_RESOURCE_ID_RE.match(value):
            continue  # Terraform Cloud/Enterprise resource ID, not a secret
        if looks_like_identifier(value):
            continue  # a code identifier (CamelCase / snake_case words, OOXML schema type), not a secret
        h = shannon_entropy(value)
        if h >= entropy_threshold(value):
            redacted = value[:4] + '...' + value[-4:] if len(value) > 12 else '***'
            print(f'{redacted}\t{h:.2f}\t{line.strip()}')
"
}
# Helper function: Check staged changes for secrets/credentials
# Returns 0 if safe to proceed, 1 if secrets found and user wants to abort
function _check_for_secrets() {
  local auto_mode="${1:-false}"
  local diff_output=$(git diff --cached)
  local added_lines=$(echo "$diff_output" | grep "^+" | grep -v "^+++")
  
  # Filter out false positives: comments, grep patterns, function definitions, variable names
  # Keep only lines that might contain actual secrets
  local filtered_lines=$(echo "$added_lines" | \
    grep -vE '^\+\s*(#|//|/\*)' | \
    grep -v 'grep.*-[qE]' | \
    grep -v 'function _check_for_secrets' | \
    grep -v 'secrets_report=' | \
    grep -v 'if echo.*grep' | \
    grep -v '\.example' | \
    grep -v '\.sample' | \
    grep -v 'YOUR_.*_HERE' | \
    grep -v '<YOUR_' | \
    grep -v 'REPLACE_' | \
    grep -v 'INSERT_' || true)
  
  local secrets_found=false
  local secrets_report=""
  local suspicious_lines=""
  
  # Check for AWS credentials - look for actual AKIA keys or key=value patterns
  if echo "$filtered_lines" | grep -qE "AKIA[0-9A-Z]{16}"; then
    secrets_report="${secrets_report}  • AWS Access Key (AKIA...)\n$(_get_matching_files "AKIA[0-9A-Z]{16}")\n"
    suspicious_lines="${suspicious_lines}$(echo "$added_lines" | grep -B5 -E "AKIA[0-9A-Z]{16}" | head -14)\n"
    secrets_found=true
  fi

  if echo "$filtered_lines" | grep -qiE "(aws_access_key_id|aws_secret_access_key)\s*=\s*['\"][A-Za-z0-9/+=]{20,}"; then
    secrets_report="${secrets_report}  • AWS credentials in config format\n$(_get_matching_files "(aws_access_key_id|aws_secret_access_key)\s*=\s*['\"][A-Za-z0-9/+=]{20,}")\n"
    suspicious_lines="${suspicious_lines}$(echo "$added_lines" | grep -iB5 -E "(aws_access_key_id|aws_secret_access_key)\s*=\s*['\"]" | head -14)\n"
    secrets_found=true
  fi

  # Check for API keys - must have key= or key: with actual value
  if echo "$filtered_lines" | grep -qiE "(api[_-]?key|apikey)\s*[=:]\s*['\"][0-9a-zA-Z_\-]{32,}"; then
    secrets_report="${secrets_report}  • API key\n$(_get_matching_files "(api[_-]?key|apikey)\s*[=:]\s*['\"][0-9a-zA-Z_-]{32,}")\n"
    suspicious_lines="${suspicious_lines}$(echo "$added_lines" | grep -iB5 -E "(api[_-]?key|apikey)\s*[=:]\s*['\"][0-9a-zA-Z_\-]{32,}" | head -14)\n"
    secrets_found=true
  fi

  # Check for passwords - must be in assignment format
  # Filter out false positives: all-uppercase placeholder values (env var names/templates),
  # values ending in _PLACEHOLDER/_HASH, and lines with variable references ($VAR)
  local pw_matches=$(echo "$filtered_lines" | \
    grep -iE "(password|passwd)\s*[=:]\s*['\"][^'\"]{8,}['\"]" | \
    grep -v '_PLACEHOLDER' | \
    grep -vE "[=:]\s*['\"][A-Z][A-Z0-9_]{7,}['\"]" | \
    grep -vE "[=:]\s*['\"]?\\\$\{?[A-Za-z_]" | \
    grep -vE "[=:]\s*['\"]?\{\{" | \
    grep -viE "[=:]\s*['\"]?(changeme|change_me|password|passwd|secret|example|placeholder|foobar|test|dummy|fake|sample|your[-_]?password|mypassword|p@ssw0rd|pass1234)['\"]?\s*$")
  if [ -n "$pw_matches" ]; then
    secrets_report="${secrets_report}  • Password\n$(_get_matching_files "(password|passwd)\s*[=:]\s*['\"][^'\"]{8,}['\"]")\n"
    suspicious_lines="${suspicious_lines}$(echo "$added_lines" | grep -iB5 -E "(password|passwd)\s*[=:]\s*['\"][^'\"]{8,}['\"]" | head -14)\n"
    secrets_found=true
  fi

  # Check for tokens - must be in assignment format with sufficient length
  if echo "$filtered_lines" | grep -qiE "(secret|token|auth[_-]?token)\s*[=:]\s*['\"][0-9a-zA-Z_\-]{40,}"; then
    secrets_report="${secrets_report}  • Secret/Token\n$(_get_matching_files "(secret|token|auth[_-]?token)\s*[=:]\s*['\"][0-9a-zA-Z_-]{40,}")\n"
    suspicious_lines="${suspicious_lines}$(echo "$added_lines" | grep -iB5 -E "(secret|token|auth[_-]?token)\s*[=:]\s*['\"]" | head -14)\n"
    secrets_found=true
  fi

  # Check for OpenAI/Stripe keys - very specific patterns
  if echo "$filtered_lines" | grep -qE "sk-[a-zA-Z0-9]{32,}|pk-(live|test)_[a-zA-Z0-9]{24,}"; then
    secrets_report="${secrets_report}  • OpenAI/Stripe API key\n$(_get_matching_files "sk-[a-zA-Z0-9]{32,}|pk-(live|test)_[a-zA-Z0-9]{24,}")\n"
    suspicious_lines="${suspicious_lines}$(echo "$added_lines" | grep -B5 -E "sk-[a-zA-Z0-9]{32,}|pk-(live|test)_" | head -14)\n"
    secrets_found=true
  fi

  # Check for GitHub tokens - very specific patterns
  if echo "$filtered_lines" | grep -qE "ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}"; then
    secrets_report="${secrets_report}  • GitHub token\n$(_get_matching_files "ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}")\n"
    suspicious_lines="${suspicious_lines}$(echo "$added_lines" | grep -B5 -E "ghp_|gho_|github_pat_" | head -14)\n"
    secrets_found=true
  fi

  # Check for private keys - actual PEM format
  if echo "$filtered_lines" | grep -qE -- "-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----"; then
    secrets_report="${secrets_report}  • Private key\n$(_get_matching_files "-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----")\n"
    suspicious_lines="${suspicious_lines}$(echo "$added_lines" | grep -B5 -E -- "-----BEGIN.*PRIVATE KEY-----" | head -14)\n"
    secrets_found=true
  fi

  # Entropy-based check: catches secrets the keyword checks above miss because
  # the variable name isn't "password"/"api_key"/"token"/etc -- any
  # identifier = "value" (or identifier: "value") assignment with a 20+ char
  # value is a candidate, scored by Shannon entropy against a threshold tuned
  # per apparent charset (hex/base64/generic), independent of the name on the
  # left. Scoped to assignment syntax specifically so it doesn't flood on
  # this repo's own legitimate high-entropy content that never appears in
  # that shape: git SHAs in commit-message comments, SSH public keys (their
  # own "ssh-ed25519 <key> comment" format, not "var = value"), nix store
  # hashes (embedded in paths, not assignments).
  # Unique by (redacted value, entropy) and capped: the same value in several copies of a file would otherwise be
  # listed once per copy, and a few hundred entries make the AI analysis below unreadable and too long to answer.
  local entropy_matches=$(echo "$filtered_lines" | _entropy_scan_secrets | awk -F'\t' '!seen[$1 FS $2]++')
  if [ -n "$entropy_matches" ]; then
    local entropy_total=$(echo "$entropy_matches" | wc -l | tr -d ' ')
    secrets_report="${secrets_report}  • High-entropy value in an unrecognized field ($entropy_total distinct)\n$(echo "$entropy_matches" | head -25 | awk -F'\t' '{print "    - " $1 " (entropy " $2 ")"}')\n"
    [ "$entropy_total" -gt 25 ] && secrets_report="${secrets_report}    ... and $((entropy_total - 25)) more\n"
    suspicious_lines="${suspicious_lines}$(echo "$entropy_matches" | head -25 | awk -F'\t' '{print $3}' | cut -c1-200)\n"
    secrets_found=true
  fi

  if $secrets_found; then
    echo ""
    echo "🚨 SECRETS DETECTED IN STAGED CHANGES! 🚨"
    echo ""
    echo "Potential secrets found:"
    echo -e "$secrets_report"
    echo ""
    echo "ℹ Analyzing detections..."
    echo ""
    local review_result exit_code
    review_result=$(echo "Secrets detection flagged the following in my staged git changes. Review the full context of each match (including nearby comments) and determine whether these are real secrets or false positives.

IMPORTANT: End your analysis with exactly one of these on its own line:
- VERDICT: ALL_CLEAR (if all detections are false positives)
- VERDICT: NEEDS_REVIEW (if any detection is a real secret)

Keep the analysis short: at most 15 lines, grouping detections that are the same kind of thing.

Detections:
$(echo -e "$secrets_report" | head -60)

Context from diff (matching lines with surrounding lines for context):
$(echo -e "$suspicious_lines" | head -c 4000)" | AI_LOCAL_ALIAS=local-coder-secrets _run_ai_plain 2>&1)
    # (declared apart from the assignment: `local x=$(cmd)` makes $? the status of `local`, which is always 0, so a
    # failed analysis used to pass as a finished one)
    exit_code=$?
    if [ $exit_code -ne 0 ] || [ -z "$review_result" ]; then
      # An analysis that did not happen is not "all clear": it takes the same path as NEEDS_REVIEW below
      # (auto mode aborts, interactive offers the review/ignore/abort menu).
      review_result="⚠ AI analysis unavailable: ${review_result:-no output}. The detections above are unreviewed."
      exit_code=0
    fi
    if [ $exit_code -eq 0 ] && [ -n "$review_result" ]; then
      echo "═══════════════════════════════════════════════════════════"
      echo "$review_result"
      echo "═══════════════════════════════════════════════════════════"

      local verdict=$(echo "$review_result" | grep -oE 'VERDICT: (ALL_CLEAR|NEEDS_REVIEW)' | tail -1)

      if [[ "$verdict" == "VERDICT: ALL_CLEAR" ]]; then
        echo ""
        echo "✓ AI analysis confirms all detections are false positives. Proceeding."
        echo "$review_result" > /tmp/gpa_secrets_verdict.txt
        return 0
      fi

      if $auto_mode; then
        echo ""
        echo "✗ Auto mode: AI analysis could not confirm these are false positives — aborting."
        echo "  Review the detections and AI analysis above, fix the flagged lines, then re-run gpa --auto."
        return 1
      fi

      echo ""
      echo "  [Enter] Open in OpenCode for interactive review"
      echo "  [i]     Ignore and proceed with commit"
      echo "  [esc]   Abort commit"
      echo ""
      echo -n "Your choice: "
      read -r post_review_choice
      case "$post_review_choice" in
        $'\e')
          echo "✗ Commit aborted."
          return 1
          ;;
        [Ii])
          echo "⚠️  Proceeding with commit despite secrets warning!"
          return 0
          ;;
        *)
          echo ""
          local prompt_file="/tmp/gpa_secrets_review_$$.txt"
          {
            echo "Secrets detection flagged the following in my staged git changes. Please review the full context and advise whether these are real secrets or false positives."
            echo ""
            echo "Detections:"
            echo -e "$secrets_report"
            echo ""
            echo "Suspicious lines from diff:"
            echo -e "$suspicious_lines"
            echo ""
            echo "AI initial analysis:"
            echo "$review_result"
          } > "$prompt_file"
          local repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
          # opencode v2 rejects --model on the TUI command ("Unrecognized flag"); it uses the model from opencode.json
          (cd "$repo_root" && opencode --prompt "I have staged git changes with potential secrets. Read $prompt_file for the full context and help me review whether these are real secrets or false positives.")
          rm -f "$prompt_file"
          return 1
          ;;
      esac
    else
      echo "⚠ AI review failed. You can proceed manually."
      return 0
    fi
  fi
  
  return 0
}

# Agent attribution is not allowed in commit messages or PR titles/descriptions: AI Co-Authored-By trailers,
# "Generated with <tool>" footers, Claude Code links. gpa, gpc and gpr strip matching lines.
_AGENT_ATTRIBUTION_RE='co-authored-by:.*(claude|anthropic|copilot|openai|chatgpt|gpt|opencode|codex|gemini|cursor|aider|devin|\[bot\])|generated (with|by|using) \[?(claude|copilot|chatgpt|gpt|opencode|codex|gemini|cursor|aider|an ai|ai[^a-z]|ai$)|claude\.(com|ai)/(code|claude-code)|noreply@anthropic\.com|🤖'

