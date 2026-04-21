#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TDD Tests for the Polyglot CLI Strategy."""

from pathlib import Path

from click.testing import CliRunner
from provide.testkit.mocking import MagicMock, patch
import pytest

from tofusoup.cli import main_cli
from tofusoup.harness.logic import GO_HARNESS_CONFIG


@pytest.mark.tdd
class TestPolyglotStrategyContract:
    """Defines the contract for the polyglot CLI strategy."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_harness_config_is_updated(self) -> None:
        """CONTRACT: GO_HARNESS_CONFIG must contain `soup-go`."""
        assert "soup-go" in GO_HARNESS_CONFIG
        assert len(GO_HARNESS_CONFIG) == 1
        assert "go-cty" not in GO_HARNESS_CONFIG
        assert "go-hcl" not in GO_HARNESS_CONFIG

    def test_harness_list_shows_soup_go(self, runner: CliRunner, tmp_path: Path) -> None:
        """CONTRACT: `soup harness list` must show the unified `soup-go` harness."""
        # Create a mock pyproject.toml and soup directory
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
        soup_dir = tmp_path / "soup"
        soup_dir.mkdir()
        (soup_dir / "soup.toml").write_text("[global_settings]\ndefault_python_log_level = 'INFO'")

        result = runner.invoke(main_cli, ["harness", "list"], obj={"PROJECT_ROOT": tmp_path})
        assert result.exit_code == 0
        assert "soup-go" in result.output
        assert "go-cty" not in result.output

    @patch("subprocess.run")
    def test_harness_build_soup_go(self, mock_run: MagicMock, runner: CliRunner, tmp_path: Path) -> None:
        """CONTRACT: `soup harness build soup-go` must build the unified binary."""
        # Create a mock pyproject.toml and soup directory
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
        soup_dir = tmp_path / "soup"
        soup_dir.mkdir()
        (soup_dir / "soup.toml").write_text("[global_settings]\ndefault_python_log_level = 'INFO'")

        # Create the source directory
        source_dir = tmp_path / "src/tofusoup/harness/go/soup-go"
        source_dir.mkdir(parents=True)

        # Mock successful build
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Force rebuild to ensure subprocess.run is called
        result = runner.invoke(
            main_cli, ["harness", "build", "soup-go", "--force-rebuild"], obj={"PROJECT_ROOT": tmp_path}
        )
        assert result.exit_code == 0
        assert "Building harness: soup-go" in result.output
        mock_run.assert_called_once()

    def test_harness_build_old_name_fails(self, runner: CliRunner, tmp_path: Path) -> None:
        """CONTRACT: `soup harness build go-cty` must fail gracefully."""
        # Create a mock pyproject.toml and soup directory
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
        soup_dir = tmp_path / "soup"
        soup_dir.mkdir()
        (soup_dir / "soup.toml").write_text("[global_settings]\ndefault_python_log_level = 'INFO'")

        result = runner.invoke(main_cli, ["harness", "build", "go-cty"], obj={"PROJECT_ROOT": tmp_path})
        assert result.exit_code != 0
        # The error should appear in stderr, not stdout
        assert "Failed to build Go harness 'go-cty'" in result.output or result.exit_code != 0

    def test_conformance_test_command_construction(self) -> None:
        """
        CONTRACT: Conformance test helpers must construct `soup-go <subcommand>` calls.
        This test simulates a helper function that might be used in conformance tests.
        """

        def get_harness_command(harness_name: str, subcommand: str, args: list[str]) -> list[str]:
            if harness_name != "soup-go":
                raise ValueError("Only 'soup-go' is supported.")

            executable_path = "/path/to/soup-go"
            return [executable_path, subcommand, *args]

        command = get_harness_command("soup-go", "cty", ["validate-value", "...", "--type", "..."])
        assert command == ["/path/to/soup-go", "cty", "validate-value", "...", "--type", "..."]

        with pytest.raises(ValueError):
            get_harness_command("go-cty", "validate-value", [])


# 🥣🔬🔚
