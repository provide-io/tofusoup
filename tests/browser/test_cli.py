import pytest
from unittest.mock import patch, AsyncMock

from provide.testkit import isolated_cli_runner, click_testing_mode

from tofusoup.browser import cli as browser_cli
from tofusoup.registry.search.engine import SearchResult

# Mark all tests in this module as browser tests
pytestmark = pytest.mark.browser

def test_sui_tui_command_exists(click_testing_mode):
    """Test that the sui tui command exists and has correct help text."""
    with isolated_cli_runner() as runner:
        result = runner.invoke(browser_cli.sui_cli, ["--help"])
        assert result.exit_code == 0
        assert "Graphical UI for browsing Terraform and OpenTofu registries" in result.output
        assert "tui" in result.output


# 🍲🥄🧪🪄
