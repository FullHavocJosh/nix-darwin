#!/usr/bin/env zsh

# Script to split .zshrc_functions into individual function files
# Each function will be in its own .zshrc_function_<name> file

set -e

SCRIPT_DIR="${0:a:h}"
BASE_DIR="${SCRIPT_DIR:h}"
FUNCTIONS_FILE="${BASE_DIR}/.zshrc_functions"
FUNCTIONS_DIR="${BASE_DIR}/.zshrc_functions.d"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "${BLUE}=== Splitting .zshrc_functions into individual files ===${NC}"
echo ""

# Backup original file
echo "${YELLOW}Backing up original .zshrc_functions...${NC}"
cp "${FUNCTIONS_FILE}" "${FUNCTIONS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "${GREEN}✓ Backup created${NC}"
echo ""

# Create functions directory
echo "${YELLOW}Creating functions directory...${NC}"
mkdir -p "${FUNCTIONS_DIR}"
echo "${GREEN}✓ Directory created: ${FUNCTIONS_DIR}${NC}"
echo ""

# Extract function definitions and their line ranges
echo "${YELLOW}Extracting functions...${NC}"
typeset -A function_starts
typeset -A function_ends

# Read the file and identify function boundaries
current_function=""
line_num=0

while IFS= read -r line; do
  ((line_num++))
  
  # Check if line starts a new function
  if [[ "$line" =~ '^function [a-zA-Z_][a-zA-Z0-9_]*\(\)' ]]; then
    # Extract function name
    func_name=$(echo "$line" | sed -E 's/^function ([a-zA-Z_][a-zA-Z0-9_]*)\(\).*/\1/')
    
    # If we were tracking a previous function, close it
    if [[ -n "$current_function" ]]; then
      function_ends[$current_function]=$((line_num - 1))
    fi
    
    # Start tracking this function
    current_function="$func_name"
    function_starts[$func_name]=$line_num
  fi
done < "$FUNCTIONS_FILE"

# Close the last function
if [[ -n "$current_function" ]]; then
  function_ends[$current_function]=$line_num
fi

# Extract each function to its own file
for func_name in ${(k)function_starts}; do
  start_line=${function_starts[$func_name]}
  end_line=${function_ends[$func_name]}
  
  output_file="${FUNCTIONS_DIR}/${func_name}"
  
  echo "  Extracting ${func_name} (lines ${start_line}-${end_line}) -> ${output_file}"
  
  # Extract the function
  sed -n "${start_line},${end_line}p" "$FUNCTIONS_FILE" > "$output_file"
  
  # Make sure it ends with a newline
  echo "" >> "$output_file"
done

echo ""
echo "${GREEN}✓ Extracted ${#function_starts[@]} functions${NC}"
echo ""

# Create a loader file that sources all functions
echo "${YELLOW}Creating loader file...${NC}"
loader_file="${BASE_DIR}/.zshrc_functions_loader"

cat > "$loader_file" << 'EOF'
# Auto-generated loader for split function files
# Generated on $(date)

# Get the directory containing this script
FUNCTIONS_DIR="${${(%):-%x}:a:h}/.zshrc_functions.d"

# Source all function files in dependency order
# Helper functions first (prefixed with _)
for func_file in "${FUNCTIONS_DIR}"/_*(N); do
  source "$func_file"
done

# Then public functions
for func_file in "${FUNCTIONS_DIR}"/[^_]*(N); do
  source "$func_file"
done
EOF

echo "${GREEN}✓ Loader file created: ${loader_file}${NC}"
echo ""

echo "${BLUE}=== Split complete! ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Review the extracted functions in: ${FUNCTIONS_DIR}/"
echo "  2. Update .zshrc to source ${loader_file} instead of .zshrc_functions"
echo "  3. Test that all functions work correctly"
echo "  4. If everything works, you can remove .zshrc_functions"
echo ""
echo "To revert: restore from backup file (${FUNCTIONS_FILE}.backup.*)"
