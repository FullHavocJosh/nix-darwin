---
name: bash-defensive-patterns
description: Master defensive Bash programming techniques for production-grade scripts. Use when writing robust shell scripts, CI/CD pipelines, or system utilities requiring fault tolerance and safety.
---

# Bash Defensive Patterns

Comprehensive guidance for writing production-ready Bash scripts using defensive programming techniques, error handling, and safety best practices.

## When to Use This Skill

- Writing production automation scripts
- Building CI/CD pipeline scripts
- Creating system administration utilities
- Developing error-resilient deployment automation
- Writing scripts that must handle edge cases safely

## Core Principles

### 1. Strict Mode

```bash
#!/bin/bash
set -Eeuo pipefail  # Exit on error, unset variables, pipe failures
```

- `-E`: Inherit ERR trap in functions
- `-e`: Exit on any error
- `-u`: Exit on undefined variable
- `-o pipefail`: Pipe fails if any command fails

### 2. Error Trapping

```bash
trap 'echo "Error on line $LINENO"' ERR
trap 'echo "Cleaning up..."; rm -rf "$TMPDIR"' EXIT

TMPDIR=$(mktemp -d)
```

### 3. Variable Safety

```bash
# Always quote variables
cp "$source" "$dest"

# Required variable — fail with message if unset
: "${REQUIRED_VAR:?REQUIRED_VAR is not set}"

# Default value
: "${OPTIONAL_VAR:=default_value}"
```

## Patterns

### Pattern 1: Script Directory Detection

```bash
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT_NAME="$(basename -- "${BASH_SOURCE[0]}")"
```

### Pattern 2: Function Template

```bash
validate_file() {
    local -r file="$1"
    local -r message="${2:-File not found: $file}"
    if [[ ! -f "$file" ]]; then
        echo "ERROR: $message" >&2
        return 1
    fi
}

process_files() {
    local -r input_dir="$1"
    local -r output_dir="$2"

    [[ -d "$input_dir" ]] || { echo "ERROR: input_dir not a directory" >&2; return 1; }
    mkdir -p "$output_dir" || { echo "ERROR: Cannot create output_dir" >&2; return 1; }

    while IFS= read -r -d '' file; do
        echo "Processing: $file"
    done < <(find "$input_dir" -maxdepth 1 -type f -print0)
}
```

### Pattern 3: Argument Parsing

```bash
VERBOSE=false
DRY_RUN=false
OUTPUT_FILE=""

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]
  -v, --verbose     Enable verbose output
  -d, --dry-run     Run without making changes
  -o, --output FILE Output file path
  -h, --help        Show help
EOF
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose) VERBOSE=true; shift ;;
        -d|--dry-run) DRY_RUN=true; shift ;;
        -o|--output)  OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)    usage 0 ;;
        --)           shift; break ;;
        *)            echo "ERROR: Unknown option: $1" >&2; usage 1 ;;
    esac
done

[[ -n "$OUTPUT_FILE" ]] || { echo "ERROR: -o/--output is required" >&2; usage 1; }
```

### Pattern 4: Structured Logging

```bash
log_info()  { echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $*" >&2; }
log_warn()  { echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARN: $*" >&2; }
log_error() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; }
log_debug() { [[ "${DEBUG:-0}" == "1" ]] && echo "[$(date +'%Y-%m-%d %H:%M:%S')] DEBUG: $*" >&2 || true; }
```

### Pattern 5: Dry-Run Support

```bash
DRY_RUN="${DRY_RUN:-false}"

run_cmd() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: $*"
        return 0
    fi
    "$@"
}

run_cmd cp "$source" "$dest"
run_cmd rm "$file"
```

### Pattern 6: Graceful Signal Handling

```bash
PIDS=()

cleanup() {
    log_info "Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill -0 "$pid" 2>/dev/null && kill -TERM "$pid" 2>/dev/null || true
    done
    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
}

trap cleanup SIGTERM SIGINT

background_task &
PIDS+=($!)

wait
```

### Pattern 7: Idempotent Operations

```bash
ensure_directory() {
    local -r dir="$1"
    if [[ -d "$dir" ]]; then
        log_info "Directory already exists: $dir"
        return 0
    fi
    mkdir -p "$dir" || { log_error "Failed to create directory: $dir"; return 1; }
    log_info "Created directory: $dir"
}

ensure_config() {
    local -r config_file="$1"
    local -r default_value="$2"
    if [[ ! -f "$config_file" ]]; then
        echo "$default_value" > "$config_file"
        log_info "Created config: $config_file"
    fi
}
```

### Pattern 8: Dependency Checking

```bash
check_dependencies() {
    local -a missing_deps=()
    local -a required=("jq" "curl" "git")

    for cmd in "${required[@]}"; do
        command -v "$cmd" &>/dev/null || missing_deps+=("$cmd")
    done

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo "ERROR: Missing required commands: ${missing_deps[*]}" >&2
        return 1
    fi
}

check_dependencies
```

### Pattern 9: Safe File Operations

```bash
# NUL-safe iteration
while IFS= read -r -d '' file; do
    echo "Processing: $file"
done < <(find /path -type f -print0)

# Atomic file write
atomic_write() {
    local -r target="$1"
    local tmpfile
    tmpfile=$(mktemp) || return 1
    cat > "$tmpfile"
    mv "$tmpfile" "$target"
}

# Safe array iteration
declare -a items=("item 1" "item 2" "item 3")
for item in "${items[@]}"; do
    echo "Processing: $item"
done
```

## Best Practices

1. **Always use strict mode** — `set -Eeuo pipefail`
2. **Quote all variables** — `"$variable"` prevents word splitting
3. **Use `[[ ]]`** — more robust than `[ ]`
4. **Implement error trapping** — catch and handle errors gracefully
5. **Validate all inputs** — check file existence, permissions
6. **Use `command -v`** — safer than `which` for checking executables
7. **Support dry-run mode** — allow previewing changes
8. **Handle temporary files safely** — use `mktemp`, cleanup with `trap`
9. **Design for idempotency** — scripts safe to rerun
10. **Use `printf` over `echo`** — more predictable across systems
