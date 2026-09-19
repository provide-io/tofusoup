# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from click.testing import CliRunner

from tofusoup.cli import main_cli


def test_lint_command_is_listed_and_describes_both_lanes() -> None:
    result = CliRunner().invoke(main_cli, ["lint", "--help"])

    assert result.exit_code == 0, result.output
    assert "Direct provider validation" in result.output
    assert "OpenTofu native linting" in result.output
    assert "--provider" in result.output
    assert "--opentofu" in result.output
