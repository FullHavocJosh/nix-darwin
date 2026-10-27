#!/usr/bin/env zsh

# Test script for _tuios_dev_peer and related functions
# This script shadows the functions to log their calls without making real SSH or tuios calls

# Create a temporary directory for logging
tmpdir=$(mktemp -d)
log_file="$tmpdir/calls.log"
all_log_file="$tmpdir/all.log"

# Function to log calls
log_call() {
    echo "$*" >> "$log_file"
    echo "$*" >> "$all_log_file"
}

# Source the original functions
source "${0:A:h}/../../../.zshrc_functions_tuios"

# Shadow the functions to log their calls instead of executing them
ssh() {
    log_call "ssh $*"
    return $FAKE_SSH_RC
}

hostname() {
    log_call "hostname $*"
    echo "$FAKE_HOST"
}

_tuios_cmd() {
    log_call "_tuios_cmd $*"
    if [[ "$1" == "hosts" ]]; then
        echo "$FAKE_HOSTS"
    fi
    return 0
}

_tuios_guard() {
    log_call "_tuios_guard $*"
    return 0
}

# Helper function to check test results
check() {
    local name="$1"
    local condition="$2"
    if eval "$condition"; then
        echo "PASS $name"
    else
        echo "FAIL $name"
        ((failures++))
    fi
}

# Initialize failure counter
failures=0

# Test cases
echo "Running tests..."

# Test 1: FAKE_HOST=MacBookM2Pro: _tuios_peer prints "mini havoc@macminim1.rollet.family"
echo "Test 1: MacBookM2Pro peer"
rm -f "$log_file"
FAKE_HOST="MacBookM2Pro"
FAKE_SSH_RC=0
result=$(_tuios_peer)
check "peer MacBookM2Pro" "[ \"$result\" = \"mini havoc@macminim1.rollet.family\" ]"

# Test 2: FAKE_HOST=MacMiniM1: _tuios_peer prints "macbook havoc@macbookm2pro.rollet.family"
echo "Test 2: MacMiniM1 peer"
rm -f "$log_file"
FAKE_HOST="MacMiniM1"
FAKE_SSH_RC=0
result=$(_tuios_peer)
check "peer MacMiniM1" "[ \"$result\" = \"macbook havoc@macbookm2pro.rollet.family\" ]"

# Test 3: FAKE_HOST=other: _tuios_peer prints nothing and returns 1

echo "Test 3: Other host peer"
rm -f "$log_file"
FAKE_HOST="OtherHost"
FAKE_SSH_RC=0
result=$(_tuios_peer); rc=$?
# Test both that result is empty AND that function returns 1
if [ -z "$result" ] && [ "$rc" -eq 1 ]; then
    echo "PASS peer other host prints nothing and returns 1"
else
    echo "FAIL peer other host prints nothing and returns 1"
    ((failures++))
fi

# Test 4: FAKE_SSH_RC=1: _tuios_peer_up returns 1
echo "Test 4: SSH failure"
rm -f "$log_file"
FAKE_HOST="MacBookM2Pro"
FAKE_SSH_RC=1
result=$(_tuios_peer_up "havoc@macminim1.rollet.family")
check "peer_up SSH failure" "[ $? -eq 1 ]"

# Test 5: FAKE_SSH_RC=0: _tuios_peer_up returns 0
echo "Test 5: SSH success"
rm -f "$log_file"
FAKE_HOST="MacBookM2Pro"
FAKE_SSH_RC=0
result=$(_tuios_peer_up "havoc@macminim1.rollet.family")
check "peer_up SSH success" "[ $? -eq 0 ]"

# Test 6: TUIOS_DEV_NO_PEER=1: _tuios_dev_peer makes no ssh call
echo "Test 6: TUIOS_DEV_NO_PEER=1"
rm -f "$log_file"
FAKE_HOST="MacBookM2Pro"
FAKE_SSH_RC=0
TUIOS_DEV_NO_PEER=1
_tuios_dev_peer
ssh_calls=$(grep -c "^ssh " "$log_file" 2>/dev/null || echo 0)
check "dev_peer no SSH with TUIOS_DEV_NO_PEER=1" "[ $ssh_calls -eq 0 ]"

# Test 7: FAKE_HOST=MacBookM2Pro, FAKE_SSH_RC=1: _tuios_dev_peer prints "not reachable" and returns 0
echo "Test 7: SSH failure with reachable check"
rm -f "$log_file"
FAKE_HOST="MacBookM2Pro"
FAKE_SSH_RC=1
TUIOS_DEV_NO_PEER=""
result=$(_tuios_dev_peer 2>&1); rc=$?
# For this test, verify it prints 'not reachable' and returns 0
check "dev_peer returns 0 with SSH failure" "[ $rc -eq 0 ]"
check "dev_peer prints not reachable with SSH failure" "[[ \"$result\" == *\"not reachable\"* ]]"

# Test 8: FAKE_SSH_RC=0, FAKE_HOSTS empty: _tuios_dev_peer should make an ssh call to run dev --detached
# and print the hint, but never call `hosts add`
echo "Test 8: SSH success with empty hosts"
rm -f "$log_file"
FAKE_HOST="MacBookM2Pro"
FAKE_SSH_RC=0
FAKE_HOSTS=""
TUIOS_DEV_NO_PEER=""
result=$(_tuios_dev_peer 2>&1)
# Check that the remote dev runs detached with TUIOS_DEV_NO_PEER=1
if grep -q "^ssh .*TUIOS_DEV_NO_PEER=1" "$log_file" 2>/dev/null && grep -q "dev --detached" "$log_file" 2>/dev/null; then
    echo "PASS dev_peer SSH success with dev --detached"
else
    echo "FAIL dev_peer SSH success with dev --detached"
    ((failures++))
fi
# The host is never added from here
if ! grep -q "hosts add" "$log_file" 2>/dev/null; then
    echo "PASS dev_peer never calls hosts add when host is missing"
else
    echo "FAIL dev_peer never calls hosts add when host is missing"
    ((failures++))
fi
# The hint about `tuios config apply` is printed when the host is not linked
check "dev_peer prints config apply hint when host is missing" \
    "[[ \"$result\" == *\"tuios: host mini is not linked yet; run 'tuios config apply' in a terminal outside tuios\"* ]]"

# Test 9: FAKE_HOSTS=mini: no `hosts add` call is logged (since it already exists)

echo "Test 9: Host already exists"
rm -f "$log_file"
FAKE_HOST="MacBookM2Pro"
FAKE_SSH_RC=0
FAKE_HOSTS="mini"
TUIOS_DEV_NO_PEER=""
result=$(_tuios_dev_peer 2>&1)
# Check that there are no hosts add calls and nothing is printed
if ! grep -q "hosts add" "$log_file" 2>/dev/null; then
    echo "PASS dev_peer no hosts add when already exists"
else
    echo "FAIL dev_peer no hosts add when already exists"
    ((failures++))
fi
check "dev_peer prints nothing when host already exists" "[ -z \"$result\" ]"

# Test 10: mmdev with no argument logs a `new --host mini` call with no extra empty argument
echo "Test 10: mmdev no argument"
rm -f "$log_file"
FAKE_HOST="MacBookM2Pro"
FAKE_SSH_RC=0
mmdev
# The logged call must be exactly 'new --host mini': no extra empty argument
if grep -qx "_tuios_cmd new --host mini" "$log_file" 2>/dev/null; then
    echo "PASS mmdev no extra empty argument"
else
    echo "FAIL mmdev no extra empty argument"
    ((failures++))
fi

# Test 11: peerdev with no argument returns 1
echo "Test 11: peerdev no argument"
rm -f "$log_file"
result=$(peerdev 2>&1)
check "peerdev no argument returns 1" "[ $? -eq 1 ]"

# Final check: no `hosts add` call is ever logged during the whole run
if ! grep -q "hosts add" "$all_log_file" 2>/dev/null; then
    echo "PASS no hosts add call was ever logged"
else
    echo "FAIL no hosts add call was ever logged"
    ((failures++))
fi

# Cleanup
rm -rf "$tmpdir"

# Exit with failure if any tests failed
if [ $failures -gt 0 ]; then
    exit 1
else
    exit 0
fi