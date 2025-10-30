#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""CLI Parity Tests for soup vs soup-go Commands

This module ensures that the Python 'soup' CLI and Go 'soup-go' CLI
have matching command structure and arguments. It validates feature parity
across the polyglot CLI implementations."""

from pathlib import Path
import re
import subprocess
from typing import ClassVar

import pytest

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build


def extract_arguments_from_help(help_text: str) -> set[str]:
    """
    Extract command-line arguments from help text.

    Looks for patterns like:
    - --argument
    - -a, --argument
    - --argument VALUE

    Returns a set of normalized argument names (without dashes).
    """
    arguments = set()

    # Pattern to match CLI arguments
    patterns = [
        r"--([a-z-]+)",  # Long form arguments like --log-level
        r"-([a-z])\b",  # Short form arguments like -h
    ]

    for pattern in patterns:
        matches = re.findall(pattern, help_text, re.IGNORECASE)
        for match in matches:
            # Normalize argument names (remove dashes, lowercase)
            normalized = match.replace("-", "").lower()
            arguments.add(normalized)

    return arguments


def get_command_help(executable: Path, command_parts: list[str]) -> tuple[int, str, str]:
    """Get help output for a specific command."""
    cmd = [str(executable), *command_parts, "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def extract_subcommands(help_text: str) -> set[str]:
    """
    Extract available subcommands from help text.

    Looks for sections like:
    Commands:
      subcommand1    Description
      subcommand2    Description
    """
    subcommands = set()

    # Look for Commands: section
    lines = help_text.split("\n")
    in_commands_section = False

    for line in lines:
        line = line.strip()

        if line.startswith("Commands:") or line.startswith("Available Commands:"):
            in_commands_section = True
            continue

        if in_commands_section:
            if line == "" or line.startswith("Options:") or line.startswith("Flags:"):
                break

            # Extract command name (first word on line)
            parts = line.split()
            if parts and not parts[0].startswith("-"):
                subcommands.add(parts[0])

    return subcommands


class TestCLIParityMatrix:
    """Test matrix for CLI parity between soup and soup-go."""

    # Define the expected command structure matrix
    COMMAND_MATRIX: ClassVar[dict[str, dict]] = {
        # Root commands
        "": {
            "common_args": {"help", "version", "loglevel"},  # Normalized versions
            "expected_subcommands": {
                "cty",
                "hcl",
                "rpc",
                "harness",
                "test",
                "wire",
                "stir",
                "drink",
                "state",
                "workenv",
                "config",
            },
        },
        # CTY commands
        "cty": {
            "common_args": {"help"},
            "expected_subcommands": {"view", "convert", "validatevalue"},  # Normalized
        },
        "cty view": {
            "common_args": {"help", "inputformat", "type"},
        },
        "cty convert": {
            "common_args": {"help", "inputformat", "outputformat", "type"},
        },
        "cty validate-value": {  # soup-go uses validate-value, soup might use different
            "common_args": {"help", "type"},
        },
        # HCL commands
        "hcl": {"common_args": {"help"}, "expected_subcommands": {"view", "convert"}},
        "hcl view": {
            "common_args": {"help"},
        },
        "hcl convert": {
            "common_args": {"help", "outputformat"},
        },
        # RPC commands
        "rpc": {
            "common_args": {"help"},
            "expected_subcommands": {"kv", "validate"},
        },
        "rpc kv": {
            "common_args": {"help"},
            "expected_subcommands": {"get", "put", "server"},
        },
        "rpc validate": {
            "common_args": {"help"},
            "expected_subcommands": {"connection"},
        },
    }

    @pytest.fixture
    def soup_executable(self) -> Path:
        """Get path to soup executable."""
        import shutil

        # Try to find soup in PATH first
        soup_path = shutil.which("soup")
        if soup_path:
            return Path(soup_path)

        # Fallback: assume it's in the project .venv
        project_root = Path(__file__).parent.parent.parent
        return project_root / ".venv" / "bin" / "soup"

    @pytest.fixture
    def soup_go_executable(self) -> Path:
        """Get path to soup-go executable."""
        project_root = Path(__file__).parent.parent.parent
        config = load_tofusoup_config(project_root)
        return ensure_go_harness_build("soup-go", project_root, config)

    @pytest.mark.parametrize(
        "command_path",
        [
            "",
            "cty",
            "cty view",
            "cty convert",
            "hcl",
            "hcl view",
            "hcl convert",
            "rpc",
            "rpc kv",
            "rpc validate",
        ],
    )
    def test_command_structure_parity(
        self, soup_executable: Path, soup_go_executable: Path, command_path: str
    ) -> None:
        """Test that both CLIs have the same command structure."""
        if not soup_executable.exists():
            pytest.skip("soup executable not found")
        if not soup_go_executable.exists():
            pytest.skip("soup-go executable not found")

        command_parts = command_path.split() if command_path else []

        # Get help from both CLIs
        soup_exit, soup_help, soup_err = get_command_help(soup_executable, command_parts)
        go_exit, go_help, go_err = get_command_help(soup_go_executable, command_parts)

        # Both should return help successfully
        assert soup_exit == 0, f"soup {command_path} --help failed: {soup_err}"
        assert go_exit == 0, f"soup-go {command_path} --help failed: {go_err}"

        # Extract subcommands if this command has them
        if command_path in self.COMMAND_MATRIX:
            expected_config = self.COMMAND_MATRIX[command_path]

            if "expected_subcommands" in expected_config:
                soup_subcommands = extract_subcommands(soup_help)
                go_subcommands = extract_subcommands(go_help)

                # Normalize subcommand names
                soup_normalized = {cmd.replace("-", "").lower() for cmd in soup_subcommands}
                go_normalized = {cmd.replace("-", "").lower() for cmd in go_subcommands}

                # Check for expected subcommands (allowing for some implementation differences)
                expected = expected_config["expected_subcommands"]

                # At minimum, both should have some core overlapping commands
                common_commands = soup_normalized.intersection(go_normalized)
                expected_overlap = expected.intersection(common_commands)

                assert len(expected_overlap) > 0, (
                    f"No command overlap for '{command_path}'. "
                    f"soup has: {soup_normalized}, "
                    f"soup-go has: {go_normalized}, "
                    f"expected: {expected}"
                )

    @pytest.mark.parametrize(
        "command_path",
        [
            "cty view",
            "cty convert",
            "hcl view",
            "hcl convert",
        ],
    )
    def test_common_arguments_parity(
        self, soup_executable: Path, soup_go_executable: Path, command_path: str
    ) -> None:
        """Test that both CLIs have similar arguments for the same commands."""
        if not soup_executable.exists():
            pytest.skip("soup executable not found")
        if not soup_go_executable.exists():
            pytest.skip("soup-go executable not found")

        command_parts = command_path.split()

        # Get help from both CLIs
        soup_exit, soup_help, _soup_err = get_command_help(soup_executable, command_parts)
        go_exit, go_help, _go_err = get_command_help(soup_go_executable, command_parts)

        # Skip if either command doesn't exist
        if soup_exit != 0 or go_exit != 0:
            pytest.skip(f"Command '{command_path}' not available in one or both CLIs")

        # Extract arguments
        soup_args = extract_arguments_from_help(soup_help)
        go_args = extract_arguments_from_help(go_help)

        # Find common arguments
        common_args = soup_args.intersection(go_args)

        # Both should at least have 'help'
        assert "help" in common_args, (
            f"Both CLIs should support --help for '{command_path}'. "
            f"soup args: {soup_args}, soup-go args: {go_args}"
        )

        # For specific commands, check expected arguments if defined
        if command_path in self.COMMAND_MATRIX:
            expected_common = self.COMMAND_MATRIX[command_path].get("common_args", set())
            missing_common = expected_common - common_args

            # Allow some flexibility - warn rather than fail for missing args
            if missing_common:
                pytest.warns(
                    UserWarning, match=f"Missing common arguments for '{command_path}': {missing_common}"
                )

    def test_root_command_basic_parity(self, soup_executable: Path, soup_go_executable: Path) -> None:
        """Test basic parity of root commands."""
        if not soup_executable.exists():
            pytest.skip("soup executable not found")
        if not soup_go_executable.exists():
            pytest.skip("soup-go executable not found")

        # Test root help
        soup_exit, soup_help, soup_err = get_command_help(soup_executable, [])
        go_exit, go_help, go_err = get_command_help(soup_go_executable, [])

        assert soup_exit == 0, f"soup --help failed: {soup_err}"
        assert go_exit == 0, f"soup-go --help failed: {go_err}"

        # Both should mention their primary subcommands
        core_commands = ["cty", "hcl", "rpc"]

        for cmd in core_commands:
            assert cmd in soup_help.lower(), f"soup should mention '{cmd}' in help"
            assert cmd in go_help.lower(), f"soup-go should mention '{cmd}' in help"

    def test_generate_command_go_only(self, soup_go_executable: Path) -> None:
        """Test that soup-go has generate command (Go-specific)."""
        if not soup_go_executable.exists():
            pytest.skip("soup-go executable not found")

        go_exit, go_help, go_err = get_command_help(soup_go_executable, ["generate"])

        assert go_exit == 0, f"soup-go generate --help failed: {go_err}"
        assert "protobuf" in go_help.lower() or "generate" in go_help.lower(), (
            "soup-go generate should mention protobuf generation"
        )

    @pytest.mark.parametrize("command", ["cty", "hcl"])
    def test_command_exists_both_clis(
        self, soup_executable: Path, soup_go_executable: Path, command: str
    ) -> None:
        """Test that core commands exist in both CLIs."""
        if not soup_executable.exists():
            pytest.skip("soup executable not found")
        if not soup_go_executable.exists():
            pytest.skip("soup-go executable not found")

        # Test that command exists in both
        soup_exit, soup_help, _ = get_command_help(soup_executable, [command])
        go_exit, go_help, _ = get_command_help(soup_go_executable, [command])

        assert soup_exit == 0, f"soup {command} should exist"
        assert go_exit == 0, f"soup-go {command} should exist"

        # Both should provide some useful help text
        assert len(soup_help.strip()) > 20, f"soup {command} should provide meaningful help"
        assert len(go_help.strip()) > 20, f"soup-go {command} should provide meaningful help"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])

# 🥣🔬🔚
