#!/usr/bin/env bash
set -euo pipefail

# Test scripts/llama-reviewer-proxy.sh with --check only; nothing is started or bound

script_path="$(dirname "$0")/llama-reviewer-proxy.sh"
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

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

expect_true() {
	local desc="$1"
	shift

	if "$@"; then
		echo "ok $desc"
	else
		echo "FAIL $desc"
		failures=$((failures + 1))
	fi
}

# Run the launcher with --check against a key file and extra env
run_proxy() {
	local key_file="$1"
	shift
	env KEY_FILE="$key_file" STATE_DIR="$tmp_dir/state" LISTEN_ADDR=127.0.0.1 "$@" "$script_path" --check
}

write_key() {
	local file="$1"
	local content="$2"
	local mode="${3:-600}"

	printf '%s' "$content" >"$file"
	chmod "$mode" "$file"
}

# Print a random 40-char alphanumeric key (subshell and || true keep pipefail quiet on SIGPIPE)
gen_key() {
	(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 40) || true
}

# Cases that need no nginx

# 1. Exit 1: key file missing
expect_exit 1 "missing key file" \
	run_proxy "$tmp_dir/missing-key" NGINX_BIN=/usr/bin/true

# 2. Exit 1: empty key file
write_key "$tmp_dir/empty-key" ""
expect_exit 1 "empty key file" \
	run_proxy "$tmp_dir/empty-key" NGINX_BIN=/usr/bin/true

# 3. Exit 1: key file mode 644
write_key "$tmp_dir/open-key" "$(gen_key)" 644
expect_exit 1 "key file mode 644" \
	run_proxy "$tmp_dir/open-key" NGINX_BIN=/usr/bin/true

# 4. Exit 1: key with a space, a double quote or a semicolon
write_key "$tmp_dir/space-key" "abc def"
expect_exit 1 "key with a space" \
	run_proxy "$tmp_dir/space-key" NGINX_BIN=/usr/bin/true
write_key "$tmp_dir/quote-key" 'abc"def'
expect_exit 1 "key with a double quote" \
	run_proxy "$tmp_dir/quote-key" NGINX_BIN=/usr/bin/true
write_key "$tmp_dir/semi-key" "abc;def"
expect_exit 1 "key with a semicolon" \
	run_proxy "$tmp_dir/semi-key" NGINX_BIN=/usr/bin/true

# 5. Exit 1: LISTEN_ADDR 0.0.0.0 with a valid key
good_key="$(gen_key)"
write_key "$tmp_dir/good-key" "$good_key"
expect_exit 1 "LISTEN_ADDR 0.0.0.0" \
	run_proxy "$tmp_dir/good-key" NGINX_BIN=/usr/bin/true LISTEN_ADDR=0.0.0.0

# 6. Exit 1: NGINX_BIN points at a missing path
expect_exit 1 "NGINX_BIN missing path" \
	run_proxy "$tmp_dir/good-key" NGINX_BIN="$tmp_dir/no-such-nginx"

# 7. Fail-closed cases must not write a config
expect_true "no config written by the failing cases" \
	test ! -e "$tmp_dir/state/nginx.conf"

# Cases that need nginx

nginx_bin="${NGINX_BIN:-}"
if [[ -z $nginx_bin ]]; then
	nginx_bin=$(command -v nginx || true)
fi

if [[ -z $nginx_bin ]]; then
	echo "skip nginx -t cases"
else
	conf="$tmp_dir/state/nginx.conf"
	out="$tmp_dir/out.txt"

	# 8. Exit 0: valid key
	run_rc=0
	run_proxy "$tmp_dir/good-key" NGINX_BIN="$nginx_bin" >"$out" 2>&1 || run_rc=$?
	if [[ $run_rc -eq 0 ]]; then
		echo "ok valid key passes nginx -t"
	else
		echo "FAIL valid key passes nginx -t (got $run_rc)"
		failures=$((failures + 1))
	fi

	# 9. Key never appears in stdout or stderr
	expect_true "key not in stdout or stderr" \
		bash -c '! grep -qF -- "$1" "$2"' _ "$good_key" "$out"

	# 10. Config mode, key count and listen address
	expect_true "nginx.conf mode 600" \
		test "$(stat -L -f %Lp "$conf")" = "600"
	expect_true "nginx.conf contains the key once" \
		test "$(grep -cF -- "$good_key" "$conf")" = "1"
	expect_true "nginx.conf listens on 127.0.0.1:" \
		grep -qF 'listen 127.0.0.1:' "$conf"

	# 11. Rotation: a new key changes the config
	new_key="$(gen_key)"
	write_key "$tmp_dir/good-key" "$new_key"
	run_rc=0
	run_proxy "$tmp_dir/good-key" NGINX_BIN="$nginx_bin" >"$out" 2>&1 || run_rc=$?
	if [[ $run_rc -eq 0 ]]; then
		echo "ok rotated key passes nginx -t"
	else
		echo "FAIL rotated key passes nginx -t (got $run_rc)"
		failures=$((failures + 1))
	fi
	expect_true "rotation puts the new key in nginx.conf" \
		grep -qF -- "$new_key" "$conf"
	expect_true "rotation removes the old key from nginx.conf" \
		bash -c '! grep -qF -- "$1" "$2"' _ "$good_key" "$conf"
	expect_true "rotated key not in stdout or stderr" \
		bash -c '! grep -qF -- "$1" "$2"' _ "$new_key" "$out"
fi

# Print final result
if [[ $failures -gt 0 ]]; then
	echo "$failures failures"
	exit 1
else
	echo "0 failures"
	exit 0
fi
