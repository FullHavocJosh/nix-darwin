#!/usr/bin/env bash
set -euo pipefail

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir" 2>/dev/null || true' EXIT

failures=0

test_case() {
    local case_name="$1"
    local npm_rc="${2:-1}"
    local expected_exit="$3"
    local expected_status_content="$4"
    local should_contain_upgrades_failures="${5:-false}"

    echo "Test case $case_name: NPM_RC=$npm_rc"

    # Create stub bin directory with stub scripts
    mkdir -p "$tmp_dir/bin"
    
    # Create stub brew script
    cat > "$tmp_dir/bin/brew" << 'EOF'
#!/bin/bash
echo "brew"
exit 0
EOF
    chmod +x "$tmp_dir/bin/brew"

    # Create stub npm script
    cat > "$tmp_dir/bin/npm" << 'EOF'
#!/bin/bash
echo "npm"
exit $NPM_RC
EOF
    chmod +x "$tmp_dir/bin/npm"

    # Create stub uv script
    cat > "$tmp_dir/bin/uv" << 'EOF'
#!/bin/bash
echo "uv"
exit 0
EOF
    chmod +x "$tmp_dir/bin/uv"

    # Set environment
    export NPM_RC="$npm_rc"
    export PATH="$tmp_dir/bin:/usr/bin:/bin"
    export UPGRADE_STATUS_FILE="$tmp_dir/status"

    # Run the script
    local rc=0
    bash "$(pwd)/scripts/upgrade-all.sh" >/dev/null 2>"$tmp_dir/err" || rc=$?

    # Check exit code
    if [[ $rc -eq $expected_exit ]]; then
        echo "  Exit code: OK"
    else
        echo "  FAIL: Exit code (got $rc, expected $expected_exit)"
        failures=$((failures + 1))
    fi

    # Check status file content
    if [[ -f "$tmp_dir/status" ]]; then
        local status_content=$(cat "$tmp_dir/status")
        if [[ "$status_content" == "$expected_status_content" ]]; then
            echo "  Status file: OK"
        else
            echo "  FAIL: Status file content (got '$status_content', expected '$expected_status_content')"
            failures=$((failures + 1))
        fi
    else
        echo "  FAIL: Status file not created"
        failures=$((failures + 1))
    fi

    # Check for UPGRADE FAILURES in stderr if expected
    if [[ "$should_contain_upgrades_failures" == "true" ]]; then
        if grep -q "UPGRADE FAILURES" "$tmp_dir/err"; then
            echo "  UPGRADE FAILURES message: OK"
        else
            echo "  FAIL: UPGRADE FAILURES message not found in stderr"
            failures=$((failures + 1))
        fi
    fi

    echo
}

# Test case 1: NPM_RC=1 (should fail)
test_case "1" "1" "1" "failed: npm" "true"

# Test case 2: NPM_RC=0 (should succeed)
test_case "2" "0" "0" "ok" "false"

# Test case 3: Remove uv stub (should succeed, skip uv)
rm "$tmp_dir/bin/uv"  # Remove uv stub
test_case "3" "0" "0" "ok" "false"

# Print final result
if [[ $failures -gt 0 ]]; then
    echo "$failures failures"
    exit 1
else
    echo "0 failures"
    exit 0
fi