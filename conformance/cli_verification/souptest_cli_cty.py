# tofusoup/conformance/cli_verification/souptest_cli_cty.py
import pytest
import json
from pathlib import Path
from typing import Any
import re

from tofusoup.harness.logic import ensure_go_harness_build, GO_HARNESS_CONFIG, HarnessBuildError
from tofusoup.common.exceptions import HarnessError
from tofusoup.common.utils import DecimalAwareJSONEncoder

from .shared_cli_utils import run_harness_cli

HARNESS_NAME = "soup-go"

# This test now correctly uses the generic go_harness_executable fixture
# by parameterizing it with the specific harness name it needs.
@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
def test_cty_cli_help(go_harness_executable: Path, project_root: Path, request: pytest.FixtureRequest):
    """Tests the --help output of the soup-go harness CTY commands."""
    test_id = request.node.name
    exit_code, stdout, stderr = run_harness_cli(
        go_harness_executable,
        ["cty", "--help"],
        project_root=project_root,
        harness_artifact_name=HARNESS_NAME,
        test_id=test_id
    )
    assert exit_code == 0, f"Expected exit code 0 for cty --help, got {exit_code}.\nStdout: {stdout}\nStderr: {stderr}"
    output_to_check = stderr if stderr else stdout
    assert "CTY type and value operations" in output_to_check
    assert "Available Commands:" in output_to_check
    assert "convert" in output_to_check
    assert "validate-value" in output_to_check

GET_TYPE_SCHEMA_CASES = [
    # This test does not exist in the new go-cty harness. It is removed.
]

# This entire test is removed as the `get-type-schema` command was removed from the harness.
# @pytest.mark.parametrize(...)
# def test_cty_cli_get_type_schema(...): ...

VALIDATE_CASES = [
    # This test does not exist in the new go-cty harness. It is removed.
]

# This entire test is removed as the `validate` command was removed from the harness.
# @pytest.mark.parametrize(...)
# def test_cty_cli_validate(...): ...

# 🍲🥄🧪🪄
