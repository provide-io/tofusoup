#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""A script to update the headers and footers of all python files while preserving formatting."""

import ast
import os

# A set of old footer patterns to be removed.
OLD_FOOTERS = {
    "# 📞🔌🔚",
    "# 📞🔌",
    "# 🐍🏗️🔌",
    "# 🐍🔌📄🪄",
    "# 🐍🏗️📋",
    "# 🍲🔍🔚",
    "# 🍲🥄🖥️🪄",
}

def update_file_content(file_path: str) -> None:
    """Read, update, and write the content of a single Python file, preserving original formatting."""
    if file_path.endswith(("_pb2.py", "_pb2_grpc.py")):
        print(f"Skipping generated file: {file_path}")
        return

    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    lines = original_content.splitlines()
    if not lines:
        return # Skip empty files

    # 1. Determine the first line and handle shebang
    is_executable = lines[0].startswith("#!")
    first_line = "#!/usr/bin/env python3" if is_executable else "# "
    code_to_process = original_content if not is_executable else "\n".join(lines[1:])

    docstring = '"""TODO: Add module docstring."""'
    body_content = ""

    # 2. Use AST to find where the code body starts, but don't unparse
    try:
        tree = ast.parse(code_to_process)
        docstring_node = ast.get_docstring(tree, clean=False)

        if docstring_node:
            docstring = f'"""{docstring_node}"""'
            # Find the line where the docstring ends to slice the original content
            if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
                end_lineno = tree.body[0].end_lineno
                # Slice the original lines to get the body
                body_lines = code_to_process.splitlines()[end_lineno:]
                body_content = "\n".join(body_lines).lstrip()
            else:
                 body_content = code_to_process # Fallback if AST is weird
        else:
            # If no docstring, find the first non-comment, non-empty line
            code_start_index = 0
            for i, line in enumerate(code_to_process.splitlines()):
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith("#"):
                    code_start_index = i
                    break
            body_content = "\n".join(code_to_process.splitlines()[code_start_index:])

    except (SyntaxError, ValueError) as e:
        print(f"AST parsing failed for {file_path}: {e}. Falling back to original content.")
        body_content = code_to_process

    # 3. Clean up the extracted body content from old footers
    body_lines = body_content.rstrip().splitlines()
    cleaned_lines = [line for line in body_lines if line.strip() not in OLD_FOOTERS]
    body_content = "\n".join(cleaned_lines).rstrip()

    # 4. Construct the final file content
    spdx_block = (
        "# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.\n"
        "# SPDX-License-Identifier: Apache-2.0\n"
        "#"
    )

    final_content = (
        f"{first_line}\n"
        f"{spdx_block}\n\n"
        f"{docstring}\n\n"
        f"{body_content}\n\n"
        f"# 🍲🔍🔚\n"
    )

    # 5. Write the new content back to the file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"Updated: {file_path}")
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")

def main() -> None:
    """Find and update all Python files in the specified directories."""
    search_dirs = ["tests"]
    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    update_file_content(os.path.join(root, file))

if __name__ == "__main__":
    main()
