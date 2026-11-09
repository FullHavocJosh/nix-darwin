# Returns 0 (via stdout "true"/"false") whether $1 is the repo's main
# checkout, as opposed to a linked worktree. The main checkout is the only
# one where --git-dir and --git-common-dir resolve to the same directory.
function _is_main_worktree() {
  local dir="$1"
  local git_dir common_dir
  # --path-format=absolute avoids the ambiguity where --git-dir is relative
  # for the main worktree but absolute for linked worktrees.
  git_dir=$(git -C "$dir" rev-parse --path-format=absolute --git-dir 2>/dev/null) || return 1
  common_dir=$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return 1
  [[ "$git_dir" == "$common_dir" ]]
}

# Prints the formatter the repo that holds $1 calls for: "prettier", "oxfmt", "biome" or "dprint". A prettier config (a
# .prettierrc*, a prettier.config.*, or a "prettier" key in package.json) wins; otherwise an oxfmt, biome or dprint config
# names its tool; a repo that declares none gets "prettier", as before. prettier run on an oxfmt repo rewrites files
# against its own 80 column default, which buries the real change and fails the repo's own format check.
function _repo_formatter() {
  local dir root f
  dir=$(dirname "$1")
  root=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || { echo prettier; return 0; }
  for f in .prettierrc .prettierrc.json .prettierrc.yml .prettierrc.yaml .prettierrc.js .prettierrc.cjs .prettierrc.mjs \
    .prettierrc.toml prettier.config.js prettier.config.cjs prettier.config.mjs; do
    [[ -e "$root/$f" ]] && { echo prettier; return 0; }
  done
  if [[ -f "$root/package.json" ]] && grep -q '"prettier"[[:space:]]*:' "$root/package.json" 2>/dev/null; then
    echo prettier
    return 0
  fi
  for f in .oxfmtrc.json .oxfmtrc.jsonc; do
    [[ -e "$root/$f" ]] && { echo oxfmt; return 0; }
  done
  for f in biome.json biome.jsonc; do
    [[ -e "$root/$f" ]] && { echo biome; return 0; }
  done
  for f in dprint.json .dprint.json; do
    [[ -e "$root/$f" ]] && { echo dprint; return 0; }
  done
  echo prettier
}

# True when the repo that holds $1 declares a formatter other than prettier (see _repo_formatter).
function _repo_uses_other_formatter() {
  [[ "$(_repo_formatter "$1")" != prettier ]]
}

# Prints the oxfmt binary for the repo that holds $1: the repo's own node_modules, then the main checkout's (a linked
# worktree has no install of its own), then PATH. Returns 1 when there is none.
function _find_oxfmt() {
  local dir root common cand
  dir=$(dirname "$1")
  root=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || return 1
  common=$(git -C "$root" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
  for cand in "$root/node_modules/.bin/oxfmt" "${common%/.git}/node_modules/.bin/oxfmt"; do
    if [[ -x "$cand" ]]; then
      echo "$cand"
      return 0
    fi
  done
  command -v oxfmt
}

# Runs oxfmt on the file $2: mode $1 is "check" (exit 0 when formatted) or "write" (formats in place). Exit 127 when no
# oxfmt binary is found. oxfmt ignores every file under a .worktrees path, which is where gpa works, so the file is
# formatted in a scratch copy together with the repo's oxfmt config, and "write" copies the result back. A file that the
# config ignores, or a type oxfmt does not handle, counts as formatted. Only the config at the repo root is used.
function _oxfmt_file() {
  local mode="$1" file="$2" bin root abs rel tmp cfg out rc
  bin=$(_find_oxfmt "$file") || return 127
  root=$(git -C "$(dirname "$file")" rev-parse --show-toplevel 2>/dev/null) || return 1
  abs="$(cd "$(dirname "$file")" && pwd)/$(basename "$file")"
  rel="${abs#$root/}"
  tmp=$(mktemp -d) || return 1
  mkdir -p "$tmp/$(dirname "$rel")"
  cp "$abs" "$tmp/$rel"
  for cfg in .oxfmtrc.json .oxfmtrc.jsonc; do
    [[ -f "$root/$cfg" ]] && cp "$root/$cfg" "$tmp/$cfg"
  done
  if [[ "$mode" == check ]]; then
    out=$(cd "$tmp" && "$bin" --check "$rel" 2>&1)
  else
    out=$(cd "$tmp" && "$bin" "$rel" 2>&1)
  fi
  rc=$?
  if [[ $rc -ne 0 && "$out" == *"Expected at least one target file"* ]]; then
    rc=0
  elif [[ $rc -eq 0 && "$mode" == write ]]; then
    cp "$tmp/$rel" "$abs"
  fi
  rm -rf "$tmp"
  return $rc
}

