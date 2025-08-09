"""
TDD Tests for the 'soup garnish' CLI command.
"""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from tofusoup.cli import main_cli

@pytest.mark.tdd
class TestGarnishCliContract:
    """Defines the contract for the `soup garnish` command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_garnish_command_exists(self, runner: CliRunner):
        """CONTRACT: The `soup garnish` command group must exist."""
        result = runner.invoke(main_cli, ["garnish", "--help"])
        assert result.exit_code == 0
        assert "Usage: tofusoup garnish [OPTIONS] COMMAND [ARGS]..." in result.output
        assert "scaffold" in result.output
        assert "render" in result.output

    def test_docs_command_is_removed(self, runner: CliRunner):
        """CONTRACT: The old `soup docs` command must NOT exist."""
        result = runner.invoke(main_cli, ["docs", "--help"])
        assert result.exit_code != 0
        assert "No such command 'docs'" in result.output

    @patch("tofusoup.garnish.cli.scaffold_garnish")
    def test_garnish_scaffold_invokes_correct_logic(self, mock_scaffold, runner: CliRunner):
        """CONTRACT: `soup garnish scaffold` must invoke the scaffolding logic."""
        mock_scaffold.return_value = {"resource": 1}
        result = runner.invoke(main_cli, ["garnish", "scaffold"])
        assert result.exit_code == 0
        mock_scaffold.assert_called_once()
        assert "Scaffolded 1 components" in result.output

    @patch("tofusoup.garnish.cli.generate_docs")
    def test_garnish_render_invokes_correct_logic(self, mock_render, runner: CliRunner):
        """CONTRACT: `soup garnish render` must invoke the rendering logic."""
        result = runner.invoke(main_cli, ["garnish", "render", "--force"])
        assert result.exit_code == 0
        mock_render.assert_called_once()
        assert "Documentation generation completed successfully!" in result.output


# 🍲🥄🧪🪄
