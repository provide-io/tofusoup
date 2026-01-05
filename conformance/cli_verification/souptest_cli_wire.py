#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TofuSoup conformance test module."""

import base64
import json
from pathlib import Path

import pytest

from .shared_cli_utils import run_harness_cli

HARNESS_NAME = "soup-go"


@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
def test_wire_cli_root_help(
    go_harness_executable: Path, project_root: Path, request: pytest.FixtureRequest
) -> None:
    test_id = request.node.name
    exit_code, stdout, stderr = run_harness_cli(
        go_harness_executable,
        ["wire", "--help"],
        project_root=project_root,
        harness_artifact_name=HARNESS_NAME,
        test_id=test_id,
    )
    output_to_check = stdout if stdout else stderr
    assert exit_code == 0
    assert "Encode and decode data using the wire protocol format" in output_to_check
    assert "encode" in output_to_check
    assert "decode" in output_to_check


@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
def test_wire_cli_encode_simple_string(
    go_harness_executable: Path, project_root: Path, request: pytest.FixtureRequest
) -> None:
    test_id = request.node.name
    input_json_str = json.dumps({"type": "string", "value": "test"})

    # Use HarnessRunner directly to get binary output
    from provide.testkit import HarnessRunner

    runner = HarnessRunner(project_root / "soup" / "output")
    exit_code, stdout_bytes, stderr_bytes = runner.run_binary(
        [str(go_harness_executable), "wire", "encode", "-", "-"],
        f"harness_runs/{HARNESS_NAME}/{test_id}",
        stdin=input_json_str,
    )

    assert exit_code == 0, f"Encode failed. Stderr: {stderr_bytes.decode('utf-8', errors='replace')}"

    # soup-go outputs base64-encoded MessagePack for the entire JSON input
    # First decode base64, then decode MessagePack
    import base64

    import msgpack

    # Remove trailing whitespace/newline and decode base64
    b64_output = stdout_bytes.strip()
    msgpack_bytes = base64.b64decode(b64_output)

    # Decode the MessagePack to verify the content (order doesn't matter for maps)
    decoded_data = msgpack.unpackb(msgpack_bytes, raw=False)

    expected_data = {"type": "string", "value": "test"}
    assert decoded_data == expected_data


@pytest.mark.parametrize("go_harness_executable", [HARNESS_NAME], indirect=True)
def test_wire_cli_decode_simple_string(
    go_harness_executable: Path, project_root: Path, request: pytest.FixtureRequest
) -> None:
    test_id = request.node.name
    # Use the actual MessagePack data soup-go wire encode produces (as binary)
    input_b64_str = "gqR0eXBlpnN0cmluZ6V2YWx1ZaR0ZXN0"  # {"type": "string", "value": "test"}
    input_msgpack_bytes = base64.b64decode(input_b64_str)

    exit_code, stdout, stderr = run_harness_cli(
        go_harness_executable,
        ["wire", "decode", "-", "-"],
        project_root=project_root,
        harness_artifact_name=HARNESS_NAME,
        test_id=test_id,
        stdin_input=input_msgpack_bytes,
    )
    assert exit_code == 0, f"Decode failed. Stderr: {stderr}"
    decoded_json = json.loads(stdout)
    assert decoded_json == {"type": "string", "value": "test"}


# 🥣🔬🔚
