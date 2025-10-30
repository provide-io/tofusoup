#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from provide.testkit import isolated_cli_runner
import pytest

from tofusoup.browser import cli as browser_cli

# Mark all tests in this module as browser tests
pytestmark = pytest.mark.browser


def test_sui_tui_command_exists() -> None:
    """Test that the sui tui command exists and has correct help text."""
    with isolated_cli_runner() as runner:
        result = runner.invoke(browser_cli.sui_cli, ["--help"])
        assert result.exit_code == 0
        assert "Graphical UI for browsing Terraform and OpenTofu registries" in result.output
        assert "tui" in result.output


# 🥣🔬🔚
