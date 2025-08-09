# tofusoup/conformance/cli_verification/souptest_cli_hcl.py
import pytest
import subprocess
import json
from pathlib import Path
from typing import List, Any, Tuple

from tofusoup.harness.logic import ensure_go_harness_build, GO_HARNESS_CONFIG, HarnessBuildError
from .shared_cli_utils import run_harness_cli

HARNESS_NAME = "go-hcl"

HCL_PARSE_CASES = [
    pytest.param(
        "simple_attrs.hcl",
        'string_attr = "hello"\nnumber_attr = 123',
        {"string_attr": "hello", "number_attr": 123},
        0,
        id="parse_simple_attrs"
    ),
    pytest.param("empty_file.hcl", "", None, 0, id="parse_empty_file"),
    pytest.param("syntax_error.hcl", 'attr = "missing_quote', None, 1, id="parse_syntax_error"),
]

@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
@pytest.mark.parametrize("filename, hcl_content, expected_json_output, expected_exit_code", HCL_PARSE_CASES)
def test_hcl_cli_parse(
    go_harness_executable: Path, project_root: Path, request: pytest.FixtureRequest,
    tmp_path: Path, filename: str, hcl_content: str,
    expected_json_output: Any, expected_exit_code: int
):
    test_id = request.node.callspec.id
    hcl_file = tmp_path / filename
    hcl_file.write_text(hcl_content)
    args = ["parse", str(hcl_file), "--output-format", "cty-json", "--log-level", "debug"]
    exit_code, stdout, stderr = run_harness_cli(
        go_harness_executable, args, project_root=project_root,
        harness_artifact_name=HARNESS_NAME, test_id=test_id
    )
    assert exit_code == expected_exit_code, f"HCL parse for '{filename}' failed. Exit: {exit_code}\nStderr: {stderr}"
    if expected_exit_code == 0:
        actual_output = json.loads(stdout) if stdout else None
        assert actual_output == expected_json_output

# 🍲🥄🧪🪄
