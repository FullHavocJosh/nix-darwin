# ZSH Functions Directory

This directory contains individual function files that are automatically loaded by `.zshrc_functions_loader`.

## Structure

- **Helper Functions** (prefixed with `_`): Loaded first as they may be dependencies for public functions
- **Public Functions** (no prefix): Loaded after helper functions

## Function Files

### Helper Functions (Internal)

- `_check_git_repo` - Validates current directory is a git repository
- `_check_for_secrets` - Scans for secrets in staged changes
- `_discover_latest_model` - Discovers latest AI model for a provider
- `_generate_readme` - Generates README files using AI
- `_get_ai_command` - Gets the appropriate AI command
- `_get_ai_provider` - Determines AI provider to use
- `_get_opencode_model` - Gets OpenCode model configuration
- `_gpa_auto_fix` - Automatically fixes issues found in gpa
- `_gpa_create_batches` - Creates review batches for gpa
- `_gpa_create_edit_workspace` - Creates editing workspace for gpa
- `_gpa_interactive_fix` - Interactive fix mode for gpa
- `_gpa_review_batch` - Reviews a batch of changes
- `_gpa_review_batch_with_timeout` - Reviews batch with timeout and retry
- `_linter_create_edit_workspace` - Creates workspace for linter fixes
- `_run_ai_command` - Executes AI commands
- `_run_linters` - Runs configured linters on staged files
- `_validate_github_copilot` - Validates GitHub Copilot setup
- `_validate_opencode_zen` - Validates OpenCode Zen setup
- `_validate_openrouter` - Validates OpenRouter setup

### Public Functions

- `aidev` - AI development assistant
- `aiselect` - Interactive AI provider selection
- `asc` - AI shell command helper
- `gpa` - Git Partial Add with AI code review
- `gpc` - Git Push with Commit (commit and push staged changes)
- `gpr_func` - Git Pull Request helper

## Loading Order

Functions are loaded in this order by `.zshrc_functions_loader`:

1. All helper functions (`_*`) - to ensure dependencies are available
2. All public functions - can use any helper function

## Adding New Functions

To add a new function:

1. Create a new file in this directory
2. Name it with the function name (prefix with `_` if it's a helper)
3. The loader will automatically source it on next shell startup

Example:

```bash
# Create new function file
cat > .zshrc_functions.d/my_new_function << 'EOF'
function my_new_function() {
  echo "Hello from my new function"
}
EOF

# Reload shell or source the loader
source ~/.zshrc_functions_loader
```

## Backup

Original monolithic `.zshrc_functions` file was backed up to:
`.zshrc_functions.backup.YYYYMMDD_HHMMSS`

## Revert Instructions

To revert to the monolithic file:

1. Restore the backup: `cp ~/.zshrc_functions.backup.* ~/.zshrc_functions`
2. Update `.zshrc` to source `~/.zshrc_functions` instead of `~/.zshrc_functions_loader`
3. Remove this directory: `rm -rf ~/.zshrc_functions.d/`
