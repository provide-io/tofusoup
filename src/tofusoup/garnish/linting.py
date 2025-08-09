#
# tofusoup/garnish/linting.py
#
"""Markdown linting integration for documentation generation."""

import json
from pathlib import Path
import subprocess


class MarkdownLinter:
    """Handles markdown linting for generated documentation."""

    def __init__(self, config_file: Path | None = None):
        self.config_file = config_file

    def lint_templates(self, template_dir: Path) -> tuple[bool, list[dict]]:
        """Lint template files before generation.

        Args:
            template_dir: Directory containing template files

        Returns:
            Tuple of (success, errors) where errors is a list of error dictionaries
        """
        return self._run_markdownlint(f"{template_dir}/**/*.tmpl.md")

    def lint_generated_docs(self, output_dir: Path) -> tuple[bool, list[dict]]:
        """Lint generated documentation files.

        Args:
            output_dir: Directory containing generated markdown files

        Returns:
            Tuple of (success, errors) where errors is a list of error dictionaries
        """
        return self._run_markdownlint(f"{output_dir}/**/*.md")

    def auto_fix_templates(self, template_dir: Path) -> bool:
        """Attempt to auto-fix template linting issues.

        Args:
            template_dir: Directory containing template files

        Returns:
            True if fixes were applied successfully
        """
        return self._run_markdownlint_fix(f"{template_dir}/**/*.tmpl.md")

    def auto_fix_generated_docs(self, output_dir: Path) -> bool:
        """Attempt to auto-fix generated documentation linting issues.

        Args:
            output_dir: Directory containing generated markdown files

        Returns:
            True if fixes were applied successfully
        """
        return self._run_markdownlint_fix(f"{output_dir}/**/*.md")

    def _run_markdownlint(self, pattern: str) -> tuple[bool, list[dict]]:
        """Run markdownlint-cli2 on files matching pattern.

        Args:
            pattern: Glob pattern for files to lint

        Returns:
            Tuple of (success, errors)
        """
        cmd = ["markdownlint-cli2", pattern]
        if self.config_file:
            cmd.extend(["--config", str(self.config_file)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            errors = []
            if result.returncode != 0:
                # Parse error output
                for line in result.stderr.split("\n"):
                    if line.strip() and ":" in line:
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            errors.append(
                                {
                                    "file": parts[0],
                                    "line": parts[1] if parts[1].isdigit() else None,
                                    "column": parts[2] if parts[2].isdigit() else None,
                                    "rule": parts[3].split()[0]
                                    if parts[3]
                                    else "unknown",
                                    "message": parts[3]
                                    if parts[3]
                                    else "Unknown error",
                                }
                            )

            return result.returncode == 0, errors

        except FileNotFoundError:
            raise RuntimeError(
                "markdownlint-cli2 not found. Install with: npm install -g markdownlint-cli2"
            )

    def _run_markdownlint_fix(self, pattern: str) -> bool:
        """Run markdownlint-cli2 with --fix flag.

        Args:
            pattern: Glob pattern for files to fix

        Returns:
            True if fixes were applied successfully
        """
        cmd = ["markdownlint-cli2", "--fix", pattern]
        if self.config_file:
            cmd.extend(["--config", str(self.config_file)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            return result.returncode == 0

        except FileNotFoundError:
            raise RuntimeError(
                "markdownlint-cli2 not found. Install with: npm install -g markdownlint-cli2"
            )

    def generate_lint_report(self, errors: list[dict], output_file: Path) -> None:
        """Generate a JSON report of linting errors for CI/CD integration.

        Args:
            errors: List of error dictionaries from linting
            output_file: Path to write JSON report
        """
        report = {
            "total_errors": len(errors),
            "errors_by_rule": {},
            "errors_by_file": {},
            "errors": errors,
        }

        # Group errors by rule
        for error in errors:
            rule = error.get("rule", "unknown")
            if rule not in report["errors_by_rule"]:
                report["errors_by_rule"][rule] = 0
            report["errors_by_rule"][rule] += 1

        # Group errors by file
        for error in errors:
            file_path = error.get("file", "unknown")
            if file_path not in report["errors_by_file"]:
                report["errors_by_file"][file_path] = 0
            report["errors_by_file"][file_path] += 1

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)


def apply_markdown_fixes(content: str) -> str:
    """Apply common markdown fixes to content.

    Args:
        content: Markdown content to fix

    Returns:
        Fixed markdown content
    """
    # Ensure trailing newline
    content = content.rstrip() + "\n"

    # Fix list marker spacing (convert double spaces to single)
    import re

    content = re.sub(r"^(\s*)-  ", r"\1- ", content, flags=re.MULTILINE)
    content = re.sub(r"^(\s*)\d+\.  ", r"\1\d+. ", content, flags=re.MULTILINE)

    # Add blank lines around headings
    content = re.sub(r"\n(#{1,6}\s+.*)\n(?!\n)", r"\n\1\n\n", content)
    content = re.sub(r"(?<!\n)\n(#{1,6}\s+.*)\n", r"\n\n\1\n", content)

    # Add blank lines around fenced code blocks
    content = re.sub(r"\n```(\w*)\n(?!\n)", r"\n\n```\1\n", content)
    content = re.sub(r"(?<!\n)\n```(\w*)\n", r"\n\n```\1\n", content)
    content = re.sub(r"\n```\n(?!\n)", r"\n```\n\n", content)
    content = re.sub(r"(?<!\n)\n```\n", r"\n\n```\n", content)

    return content


def break_long_lines(content: str, max_length: int = 100) -> str:
    """Break long lines at word boundaries.

    Args:
        content: Markdown content
        max_length: Maximum line length

    Returns:
        Content with lines broken at word boundaries
    """
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        if len(line) <= max_length:
            fixed_lines.append(line)
            continue

        # Skip code blocks and headings
        if line.startswith("```") or line.startswith("#"):
            fixed_lines.append(line)
            continue

        # Break at word boundaries
        words = line.split(" ")
        current_line = ""

        for word in words:
            if len(current_line + " " + word) <= max_length:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    fixed_lines.append(current_line)
                current_line = word

        if current_line:
            fixed_lines.append(current_line)

    return "\n".join(fixed_lines)


# 🍲🥄📄🪄
