#!/usr/bin/env zsh
# Review routing in _run_aider_local: gateway when a review backend is healthy, loopback otherwise.
# Stubs curl and aider on PATH; no network. Run: zsh test_review_gateway.zsh
ROOT="${0:A:h:h:h:h}/.zsh_functions/ai"
T=$(mktemp -d); mkdir "$T/bin"; fails=0
printf '#!/bin/sh\ncat >/dev/null\necho "$STUB_TIERS"\n' > "$T/bin/curl"
printf '#!/bin/sh\necho "BASE=$(echo "$*" | grep -o "api-base [^ ]*")"; echo "KEY=${OPENAI_API_KEY:+set}"; echo "ARGKEY=$(echo "$*" | grep -c sk-local)"\n' > "$T/bin/aider"
printf '#!/bin/sh\nexit 1\n' > "$T/bin/doppler"  # no real Doppler in tests
chmod +x "$T/bin/"*
run() {  # alias, then env assignments
  local a="$1"; shift
  env PATH="$T/bin:$PATH" HOME="$T" "$@" zsh -c "source $ROOT/25-llm-gateway.zsh; source $ROOT/20-aider-local.zsh; _llamacpp_profile_load(){return 1}; _run_aider_local $a 5 hi" 2>&1
}
check() { if [[ "$2" == *"$3"* ]]; then echo "PASS $1"; else echo "FAIL $1: $2"; fails=1; fi }
UP='{"groups":{"review":[{"id":"cait-g14","healthy":true}]}}'
DOWN='{"groups":{"review":[{"id":"cait-g14","healthy":false},{"id":"macmini-m1","healthy":false}]}}'
out=$(run local-coder-review STUB_TIERS="$UP" AISTACK_GATEWAY_KEY=k)
check "review uses gateway when healthy" "$out" "auto/v1"; check "gateway key goes by env" "$out" "KEY=set"; check "no sk-local arg on gateway" "$out" "ARGKEY=0"
out=$(run local-coder-review STUB_TIERS="$DOWN" AISTACK_GATEWAY_KEY=k)
check "review falls back to loopback when all down" "$out" "127.0.0.1:8080"
out=$(run local-coder-review STUB_TIERS="$UP" AISTACK_GATEWAY_KEY=k AISTACK_REVIEW_GATEWAY=off)
check "off switch keeps loopback" "$out" "127.0.0.1:8080"
out=$(run local-coder-review STUB_TIERS="$UP")
check "no key keeps loopback" "$out" "127.0.0.1:8080"
out=$(run local-coder-commit STUB_TIERS="$UP" AISTACK_GATEWAY_KEY=k)
check "commit alias never uses gateway" "$out" "127.0.0.1:8080"
rm -rf "$T"; exit $fails
