#!/usr/bin/env python3
"""
Split .zshrc_functions into individual function files.
Each function will be in its own file in .zshrc_functions.d/
"""

import re
from pathlib import Path
from datetime import datetime


def find_function_boundaries(content):
    """Find start and end lines for each function."""
    lines = content.split("\n")
    functions = {}
    current_function = None
    brace_count = 0
    start_line = 0

    for i, line in enumerate(lines, 1):
        # Check if line starts a new function
        match = re.match(r"^function\s+([a-zA-Z_][a-zA-Z0-9_]*)\(\s*\)\s*\{?", line)
        if match:
            func_name = match.group(1)
            current_function = func_name
            start_line = i
            # Count opening brace if on same line
            brace_count = line.count("{") - line.count("}")
        elif current_function:
            # Track braces
            brace_count += line.count("{") - line.count("}")

            # If brace count returns to 0, we've closed the function
            if brace_count == 0 and (
                "{" in lines[start_line - 1] or lines[start_line:i]
            ):
                functions[current_function] = {
                    "start": start_line,
                    "end": i,
                    "lines": lines[start_line - 1 : i],
                }
                current_function = None
                brace_count = 0

    return functions


def main():
    base_dir = Path(__file__).parent.parent
    functions_file = base_dir / ".zshrc_functions"
    functions_dir = base_dir / ".zshrc_functions.d"

    print("=== Splitting .zshrc_functions into individual files ===\n")

    # Read the original file
    print(f"Reading {functions_file}...")
    with open(functions_file, "r") as f:
        content = f.read()

    # Create backup
    backup_file = f"{functions_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup: {backup_file}")
    with open(backup_file, "w") as f:
        f.write(content)
    print("✓ Backup created\n")

    # Create functions directory
    print(f"Creating directory: {functions_dir}")
    functions_dir.mkdir(exist_ok=True)
    print("✓ Directory created\n")

    # Extract functions
    print("Extracting functions...")
    functions = find_function_boundaries(content)

    for func_name, func_data in sorted(functions.items()):
        output_file = functions_dir / func_name
        print(
            f"  {func_name} (lines {func_data['start']}-{func_data['end']}) -> {output_file.name}"
        )

        # Write function to file
        with open(output_file, "w") as f:
            f.write("\n".join(func_data["lines"]))
            f.write("\n")

    print(f"\n✓ Extracted {len(functions)} functions\n")

    # Create loader file
    loader_file = base_dir / ".zshrc_functions_loader"
    print(f"Creating loader file: {loader_file}")

    loader_content = f"""# Auto-generated loader for split function files
# Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# Get the directory containing this script
FUNCTIONS_DIR="${{${{(%):-%x}}:a:h}}/.zshrc_functions.d"

# Source all function files in dependency order
# Helper functions first (prefixed with _)
for func_file in "${{FUNCTIONS_DIR}}"/_*(N); do
  source "$func_file"
done

# Then public functions
for func_file in "${{FUNCTIONS_DIR}}"/[^_]*(N); do
  source "$func_file"
done
"""

    with open(loader_file, "w") as f:
        f.write(loader_content)

    print("✓ Loader file created\n")

    print("=== Split complete! ===\n")
    print("Next steps:")
    print(f"  1. Review the extracted functions in: {functions_dir}/")
    print(
        f"  2. Update .zshrc to source {loader_file.name} instead of .zshrc_functions"
    )
    print("  3. Test that all functions work correctly")
    print("  4. If everything works, you can remove .zshrc_functions")
    print(f"\nTo revert: restore from {backup_file}")


if __name__ == "__main__":
    main()
