# tofusoup/conformance/cli_verification/souptest_cli_wire.py
import pytest
import json
from pathlib import Path
import base64

from .shared_cli_utils import run_harness_cli

HARNESS_NAME = "go-wire"

@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
def test_wire_cli_root_help(go_harness_executable: Path, project_root: Path, request: pytest.FixtureRequest):
    test_id = request.node.name
    exit_code, stdout, stderr = run_harness_cli(
        go_harness_executable, ["--help"], project_root=project_root,
        harness_artifact_name=HARNESS_NAME, test_id=test_id
    )
    output_to_check = stdout if stdout else stderr
    assert exit_code == 0
    assert "go-wire-harness" in output_to_check
    assert "encode" in output_to_check
    assert "decode" in output_to_check

@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
def test_wire_cli_encode_simple_string(go_harness_executable: Path, project_root: Path, request: pytest.FixtureRequest):
    test_id = request.node.name
    input_json_str = json.dumps({"type": "string", "value": "test"})
    exit_code, stdout, stderr = run_harness_cli(
        go_harness_executable, ["encode", "-"], project_root=project_root,
        harness_artifact_name=HARNESS_NAME, test_id=test_id, stdin_content=input_json_str
    )
    assert exit_code == 0, f"Encode failed. Stderr: {stderr}"
    assert stdout.strip() == "pHRlc3Q="

@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
def test_wire_cli_decode_simple_string(go_harness_executable: Path, project_root: Path, request: pytest.FixtureRequest):
    test_id = request.node.name
    input_b64_str = "pHRlc3Q="
    exit_code, stdout, stderr = run_harness_cli(
        go_harness_executable, ["decode", "-", "--type", "string"], project_root=project_root,
        harness_artifact_name=HARNESS_NAME, test_id=test_id, stdin_content=input_b64_str
    )
    assert exit_code == 0, f"Decode failed. Stderr: {stderr}"
    decoded_json = json.loads(stdout)
    assert decoded_json == "test"

# 🍲🥄🧪🪄
