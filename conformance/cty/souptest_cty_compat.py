#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TofuSoup conformance test module."""

from pathlib import Path
import subprocess

import pytest


@pytest.mark.integration_cty
@pytest.mark.harness_go
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
def test_souptest_go_cty_validation(go_harness_executable: Path) -> None:
    """
    Conformance test to verify that the `soup-go cty validate-value` command
    works as expected for a simple case.
    """
    if not go_harness_executable.exists():
        pytest.skip("Go harness executable not found.")

    # Command to validate a simple string against the string type
    # Go ctyjson.UnmarshalType expects JSON format, so "string" should be passed as "\"string\""
    cmd = [
        str(go_harness_executable),
        "cty",
        "validate-value",
        '"hello"',
        "--type",
        '"string"',
        "--log-level",
        "trace",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert result.returncode == 0, f"Go harness failed.\nStderr: {result.stderr}"
    assert "Validation Succeeded" in result.stdout


# 🥣🔬🔚
