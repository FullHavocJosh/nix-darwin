#!/usr/bin/env bash
set -euo pipefail

# Test scripts/launchd-ensure.sh without root and without loading anything

script_path="$(dirname "$0")/launchd-ensure.sh"
tmp_dir=$(mktemp -d)
trap 'rm -f "$tmp_dir"/* 2>/dev/null; rmdir "$tmp_dir" 2>/dev/null || true' EXIT

failures=0

expect_exit() {
	local want="$1"
	local desc="$2"
	shift 2
	local cmd=("$@")
	local got=0

	"${cmd[@]}" >/dev/null 2>&1 || got=$?

	if [[ $got -eq $want ]]; then
		echo "ok $desc"
	else
		echo "FAIL $desc (got $got)"
		failures=$((failures + 1))
	fi
}

# Test cases

# 1. Exit 0: --check system org.nixos.nix-daemon /Library/LaunchDaemons/org.nixos.nix-daemon.plist
expect_exit 0 "system org.nixos.nix-daemon with valid plist" \
	"$script_path" --check system org.nixos.nix-daemon /Library/LaunchDaemons/org.nixos.nix-daemon.plist

# 2. Exit 1: --check system org.nixos.launchd-ensure-test-missing "$tmp/missing.plist" (file does not exist)
expect_exit 1 "system org.nixos.launchd-ensure-test-missing with missing plist" \
	"$script_path" --check system org.nixos.launchd-ensure-test-missing "$tmp_dir/missing.plist"

# 3. Exit 1: invalid plist: write the text not a plist to "$tmp/bad.plist", then --check system org.nixos.launchd-ensure-test-bad "$tmp/bad.plist"
echo "not a plist" >"$tmp_dir/bad.plist"
expect_exit 1 "system org.nixos.launchd-ensure-test-bad with invalid plist" \
	"$script_path" --check system org.nixos.launchd-ensure-test-bad "$tmp_dir/bad.plist"

# 4. Exit 1: valid plist for a label that is not loaded: create "$tmp/unloaded.plist" with /usr/bin/plutil -create xml1, then /usr/bin/plutil -insert Label -string org.nixos.launchd-ensure-test-unloaded and /usr/bin/plutil -insert ProgramArguments -json '["/usr/bin/true"]'; run --check system org.nixos.launchd-ensure-test-unloaded "$tmp/unloaded.plist"
/usr/bin/plutil -create xml1 "$tmp_dir/unloaded.plist"
/usr/bin/plutil -insert Label -string org.nixos.launchd-ensure-test-unloaded "$tmp_dir/unloaded.plist"
/usr/bin/plutil -insert ProgramArguments -json '["/usr/bin/true"]' "$tmp_dir/unloaded.plist"
expect_exit 1 "system org.nixos.launchd-ensure-test-unloaded with unloaded plist" \
	"$script_path" --check system org.nixos.launchd-ensure-test-unloaded "$tmp_dir/unloaded.plist"

# 5. Exit 2: no arguments at all
expect_exit 2 "no arguments at all" \
	"$script_path"

# 6. Exit 2: two arguments only: system org.nixos.nix-daemon
expect_exit 2 "two arguments only: system org.nixos.nix-daemon" \
	"$script_path" system org.nixos.nix-daemon

# 7. Exit 2: bad domain: --check user org.nixos.nix-daemon /Library/LaunchDaemons/org.nixos.nix-daemon.plist
expect_exit 2 "bad domain: user instead of system" \
	"$script_path" --check user org.nixos.nix-daemon /Library/LaunchDaemons/org.nixos.nix-daemon.plist

# 8. Exit 2: gui without --user: --check gui org.nixos.set-gui-path "$tmp/unloaded.plist"
expect_exit 2 "gui without --user" \
	"$script_path" --check gui org.nixos.set-gui-path "$tmp_dir/unloaded.plist"

# Print final result
if [[ $failures -gt 0 ]]; then
	echo "$failures failures"
	exit 1
else
	echo "0 failures"
	exit 0
fi
