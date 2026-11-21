#!/usr/bin/env bash
set -euo pipefail

# nginx reverse proxy in front of the loopback 9B reviewer (llama-server).
# Requires a Bearer key read from KEY_FILE at start. Usage: llama-reviewer-proxy.sh [--check]
# Env: NGINX_BIN (required), LISTEN_ADDR (required), LISTEN_PORT, UPSTREAM, KEY_FILE, STATE_DIR

fail() {
	echo "llama-reviewer-proxy: $*" >&2
	exit 1
}

check_only=0
if [[ ${1:-} == "--check" ]]; then
	check_only=1
fi

NGINX_BIN="${NGINX_BIN:-}"
LISTEN_ADDR="${LISTEN_ADDR:-}"
LISTEN_PORT="${LISTEN_PORT:-8083}"
UPSTREAM="${UPSTREAM:-http://127.0.0.1:8080}"
KEY_FILE="${KEY_FILE:-$HOME/.config/llama-reviewer/api-key}"
STATE_DIR="${STATE_DIR:-$HOME/.local/state/llama-reviewer-proxy}"

if [[ -z $LISTEN_ADDR || $LISTEN_ADDR == "0.0.0.0" ]]; then
	fail "LISTEN_ADDR must be set to a specific address, not empty or 0.0.0.0"
fi
if [[ -z $NGINX_BIN || ! -x $NGINX_BIN ]]; then
	fail "NGINX_BIN is not executable"
fi
if [[ ! -f $KEY_FILE ]]; then
	fail "key file $KEY_FILE is missing or not a regular file"
fi
if [[ $(stat -L -f %Lp "$KEY_FILE") != "600" ]]; then
	fail "key file $KEY_FILE must have mode 600"
fi

key=$(<"$KEY_FILE")
key="${key#"${key%%[![:space:]]*}"}"
key="${key%"${key##*[![:space:]]}"}"
if [[ -z $key ]]; then
	fail "key file $KEY_FILE is empty"
fi
# The key goes into the nginx config, so only allow characters that cannot break out of a quoted string
if [[ ! $key =~ ^[A-Za-z0-9._~+/=-]+$ ]]; then
	fail "key in $KEY_FILE contains characters outside [A-Za-z0-9._~+/=-]"
fi

upstream_host="${UPSTREAM#*://}"
upstream_host="${upstream_host%%/*}"

umask 077
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"
conf="$STATE_DIR/nginx.conf"

# The 9B has one slot and llama-server queues extra requests itself, so nginx only holds the
# connection; proxy_read_timeout 600s bounds a queued request.
cat >"$conf" <<EOF
daemon off;
pid $STATE_DIR/nginx.pid;
error_log stderr warn;

events {
	worker_connections 64;
}

http {
	access_log off;
	client_body_temp_path $STATE_DIR/client_body_temp;
	proxy_temp_path $STATE_DIR/proxy_temp;
	fastcgi_temp_path $STATE_DIR/fastcgi_temp;
	uwsgi_temp_path $STATE_DIR/uwsgi_temp;
	scgi_temp_path $STATE_DIR/scgi_temp;
	client_max_body_size 32m;

	map \$http_authorization \$reviewer_ok {
		default 0;
		"Bearer $key" 1;
	}

	server {
		listen $LISTEN_ADDR:$LISTEN_PORT;

		location /v1/ {
			default_type application/json;
			if (\$reviewer_ok = 0) {
				return 401 '{"error":"unauthorized"}';
			}
			proxy_pass ${UPSTREAM%/}/v1/;
			proxy_http_version 1.1;
			proxy_set_header Connection '';
			proxy_set_header Host $upstream_host;
			proxy_set_header Authorization '';
			proxy_buffering off;
			proxy_request_buffering off;
			proxy_cache off;
			proxy_connect_timeout 5s;
			proxy_send_timeout 600s;
			proxy_read_timeout 600s;
			gzip off;
		}

		location / {
			return 404;
		}
	}
}
EOF
chmod 600 "$conf"

if [[ $check_only -eq 1 ]]; then
	exec "$NGINX_BIN" -t -c "$conf" -p "$STATE_DIR"
fi

exec "$NGINX_BIN" -c "$conf" -p "$STATE_DIR"
