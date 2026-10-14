#!/usr/bin/env bash
#
# Validate timemachine-exclusions.txt
#
# The Time Machine exclusion list (nix-darwin/timemachine-exclusions.txt) is
# applied verbatim by the nix module, so a typo there silently excludes the
# wrong directory. This script enforces the rules instead:
#
#   * one '~/' path per line, no wildcards, no duplicates
#   * no protected path (keys, config, binaries, documents, state)
#   * every required entry is present
#
# Usage: nix-darwin/scripts/check-timemachine-exclusions.sh
#
# shellcheck disable=SC2088  # the '~/' paths are compared literally, not expanded

set -euo pipefail

cd "$(dirname "$0")/.."

LIST_FILE="timemachine-exclusions.txt"
ERRORS=0

# Directories that must never be excluded, directly or as a parent: they hold
# keys, config, binaries, documents or application state that cannot be
# re-downloaded.
PROTECTED=(
    "~"
    "~/.ssh"
    "~/.config"
    "~/.gnupg"
    "~/Documents"
    "~/Desktop"
    "~/Library"
    "~/.local"
    "~/.cargo"
    "~/.ollama"
    "~/.bun"
    "~/nix-darwin"
)

# Entries the list has to contain: the replaceable caches and model stores.
REQUIRED=(
    "~/.ollama/models"
    "~/.lmstudio/models"
    "~/.cache"
    "~/.npm"
    "~/.bun/install/cache"
    "~/.cargo/registry"
    "~/.cargo/git"
    "~/.rustup/toolchains"
    "~/.gradle/caches"
    "~/.m2/repository"
    "~/.pnpm-store"
    "~/Library/pnpm/store"
    "~/go/pkg/mod"
    "~/.nuget/packages"
    "~/.terraform.d/plugin-cache"
    "~/Library/Caches"
    "~/Library/Developer/Xcode/DerivedData"
    "~/Library/Developer/CoreSimulator"
)

error() {
    printf 'error: %s\n' "$1" >&2
    ERRORS=$((ERRORS + 1))
}

# Drop trailing slashes, they are irrelevant for equality/parenthood checks.
normalize() {
    local normalized="${1%/}"
    while [[ "$normalized" == */ ]]; do
        normalized="${normalized%/}"
    done
    printf '%s' "${normalized:-/}"
}

if [[ ! -f "$LIST_FILE" ]]; then
    printf 'error: %s not found\n' "$LIST_FILE" >&2
    exit 1
fi

entries=()

while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}" # strip leading whitespace
    line="${line%"${line##*[![:space:]]}"}" # strip trailing whitespace
    if [[ -z "$line" || "$line" == "#"* ]]; then
        continue
    fi
    entries+=("$line")
done <"$LIST_FILE"

count=${#entries[@]}
if ((count == 0)); then
    printf 'error: %s has no entries\n' "$LIST_FILE" >&2
    exit 1
fi

# Newline-delimited copy of the entries, used for the required-entry lookup.
entry_list=$'\n'"$(printf '%s\n' "${entries[@]}")"$'\n'

for ((i = 0; i < count; i++)); do
    entry="${entries[i]}"
    path="$(normalize "$entry")"

    if [[ "$path" != "~/"* ]]; then
        error "$entry: must start with '~/'"
        continue
    fi

    if [[ "$path" == *"?"* || "$path" == *"*"* ]]; then
        error "$entry: wildcards are not allowed, list the directory itself"
        continue
    fi

    for protected in "${PROTECTED[@]}"; do
        # Rejected when the entry is the protected path itself, or a parent of
        # it ('~' is a parent of every protected path below the home dir).
        if [[ "$path" == "$protected" || "$protected" == "$path/"* ]]; then
            error "$entry: protected path, or a parent of one"
            break
        fi
    done

    for ((j = i + 1; j < count; j++)); do
        if [[ "$(normalize "${entries[j]}")" == "$path" ]]; then
            error "$entry: duplicate entry"
            break
        fi
    done
done

for required in "${REQUIRED[@]}"; do
    if [[ "$entry_list" != *$'\n'"$required"$'\n'* ]]; then
        error "$required: required entry is missing"
    fi
done

if ((ERRORS > 0)); then
    printf '%d problem(s) found in %s\n' "$ERRORS" "$LIST_FILE" >&2
    exit 1
fi

printf 'ok: %s entries in %s\n' "$count" "$LIST_FILE"
exit 0
