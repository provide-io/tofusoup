import pytest
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock

from tofusoup.browser import cli as browser_cli
from tofusoup.registry.search.engine import SearchResult

# Mark all tests in this module as browser tests
pytestmark = pytest.mark.browser

@pytest.fixture
def runner():
    return CliRunner()

def test_sui_tui_command_exists(runner):
    """Test that the sui tui command exists and has correct help text."""
    result = runner.invoke(browser_cli.sui_cli, ["--help"])
    assert result.exit_code == 0
    assert "Graphical UI for browsing Terraform and OpenTofu registries" in result.output
    assert "tui" in result.output


# 🍲🥄🧪🪄
