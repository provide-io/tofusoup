#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import json
from pathlib import Path
from typing import Any

import pytest

from .shared_cli_utils import run_harness_cli

HARNESS_NAME = "soup-go"

HCL_PARSE_CASES = [
    pytest.param(
        "simple_attrs.hcl",
        'string_attr = "hello"\nnumber_attr = 123',
        {"string_attr": "hello", "number_attr": 123},
        0,
        id="parse_simple_attrs",
    ),
    pytest.param("empty_file.hcl", "", None, 0, id="parse_empty_file"),
    pytest.param("syntax_error.hcl", 'attr = "missing_quote', None, 0, id="parse_syntax_error"),
]


@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
@pytest.mark.parametrize("filename, hcl_content, expected_json_output, expected_exit_code", HCL_PARSE_CASES)
def test_hcl_cli_parse(
    go_harness_executable: Path,
    project_root: Path,
    request: pytest.FixtureRequest,
    tmp_path: Path,
    filename: str,
    hcl_content: str,
    expected_json_output: Any,
    expected_exit_code: int,
) -> None:
    test_id = request.node.callspec.id
    hcl_file = tmp_path / filename
    hcl_file.write_text(hcl_content)
    args = ["hcl", "view", str(hcl_file), "--output-format", "json", "--log-level", "debug"]
    exit_code, stdout, stderr = run_harness_cli(
        go_harness_executable,
        args,
        project_root=project_root,
        harness_artifact_name=HARNESS_NAME,
        test_id=test_id,
    )
    assert exit_code == expected_exit_code, (
        f"HCL parse for '{filename}' failed. Exit: {exit_code}\nStderr: {stderr}"
    )
    if expected_exit_code == 0 and expected_json_output is not None:
        # soup-go returns output in a wrapper with "success" and "body" fields
        actual_output = json.loads(stdout) if stdout else None
        if actual_output and "body" in actual_output:
            # Extract the body for comparison
            actual_body = actual_output.get("body", {})
            assert actual_body == expected_json_output or actual_body == {"blocks": [], **expected_json_output}
        else:
            assert actual_output == expected_json_output


# 🥣🔬🔚
